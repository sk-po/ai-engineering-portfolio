from collections.abc import AsyncIterable, Awaitable, Mapping, Sequence
from math import isfinite
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import uuid4

from azure.core.exceptions import AzureError
from azure.search.documents.models import VectorizedQuery
from openai import OpenAIError
from structlog.stdlib import BoundLogger

from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.domain.models import AsvsRequirement, RequirementMatch
from app.observability import get_logger

VECTOR_DIMENSIONS = 1536
logger = get_logger(__name__)
VECTOR_FIELD = "content_vector"
SELECT_FIELDS = (
    "requirement_id",
    "chapter_id",
    "chapter_name_ja",
    "chapter_name_en",
    "section_id",
    "section_name_ja",
    "section_name_en",
    "description_ja",
    "description_en",
    "level",
    "version",
)


class AsyncEmbeddingClient(Protocol):
    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """検索文を非同期でベクトル化する。

        Args:
            texts: ベクトル化する文章の列。

        Returns:
            入力順のベクトル列。
        """
        ...


class AsyncVectorSearchClient(Protocol):
    def search(
        self, search_text: str | None = None, **kwargs: Any
    ) -> Awaitable[AsyncIterable[Mapping[str, Any]]]:
        """Azure SDKとテスト用クライアントに共通する検索契約を定義する。

        Args:
            search_text: 全文検索用の文字列。Noneは全文検索を指定しない。
            **kwargs: ベクトル、filter、取得フィールド、件数などの検索条件。

        Returns:
            文書フィールドと検索スコアを持つ非同期反復可能オブジェクト。
            反復中にも外部通信が発生する。
        """
        ...


class AzureSearchRequirementRepository:
    """Embed a query, search approved ASVS vectors, and map the results."""

    def __init__(
        self,
        embedding_client: AsyncEmbeddingClient,
        search_client: AsyncVectorSearchClient,
    ) -> None:
        """検索に必要なクライアントを受け取る。この時点では通信しない。

        Args:
            embedding_client: 登録文書と同じモデルで文章をベクトル化するクライアント。
            search_client: 対象Indexへ検索要求を送るクライアント。
        """
        self._embedding_client = embedding_client
        self._search_client = search_client

    async def search(
        self,
        query: str,
        *,
        level: int | None,
        limit: int,
        level_filter: Literal["at_most", "exact"] = "at_most",
    ) -> tuple[RequirementMatch, ...]:
        """検索文をベクトル化し、公開・承認済みASVS要件をAzureで検索する。

        Args:
            query: ユースケースで空白除去・検証済みの検索文。
            level: 対象Level。level_filterがat_mostなら上限、exactなら完全一致。
            limit: 最大取得件数。ユースケースで1〜10に検証済みであること。
            level_filter: Levelの絞り込み方法。既定at_mostは指定値以下を対象とする。

        Returns:
            Azureの返却順を保持した検索結果のタプル。該当なしは空タプル。

        Raises:
            RequirementSearchUnavailableError: SDKの通信・認証エラー、または
                ベクトルや検索結果の検証失敗。ページ取得中の失敗も含む。

        Notes:
            Embedding APIとAzure AI Searchへ非同期通信する。CSVへの自動切り替えは行わない。
            通信段階ごとの成否・所要時間と公開ASVS検索結果を同じsearch_idで記録する。
            入力文・ベクトル・認証情報・例外本文はログに含めない。
        """
        search_id = uuid4().hex
        search_logger = logger.bind(search_id=search_id)
        stage = "embedding"
        started = perf_counter()  # 開始時刻
        try:
            query_vector = await self._embed_query(query)
            _log_search_event(
                search_logger,
                stage,
                started,
                "success",
                dimensions=len(query_vector),
            )
            stage = "azure_search"
            started = perf_counter()
            results = await self._search_client.search(
                search_text=None,
                vector_queries=[
                    VectorizedQuery(
                        vector=list(query_vector),
                        k_nearest_neighbors=limit,
                        fields=VECTOR_FIELD,
                        exhaustive=False,
                    )
                ],
                filter=self._build_filter(level, level_filter),  # and...でクエリ作成
                vector_filter_mode="preFilter",
                select=list(SELECT_FIELDS),
                top=limit,
            )
            # AsyncItemPaged performs I/O during iteration as well as search().
            matches_list: list[RequirementMatch] = []
            async for result in results:
                matches_list.append(self._to_requirement_match(result))
            matches = tuple(matches_list)
            _log_search_event(
                search_logger,
                stage,
                started,
                "success",
                result_count=len(matches),
                level=level,
                level_filter=level_filter,
                limit=limit,
                results=[
                    {
                        "rank": rank,
                        "requirement_id": match.requirement.requirement_id,
                        "score": match.score,
                        "level": match.requirement.level,
                    }
                    for rank, match in enumerate(matches, start=1)
                ],
            )
            return matches
        except (AzureError, OpenAIError, ValueError, TypeError, KeyError) as error:
            status = getattr(error, "status_code", None)
            _log_search_event(
                search_logger,
                stage,
                started,
                "failure",
                error_type=type(error).__name__,
                http_status=status if type(status) is int else None,
            )
            raise RequirementSearchUnavailableError(
                "Requirement search is temporarily unavailable"
            ) from error

    async def _embed_query(self, query: str) -> tuple[float, ...]:
        """検索文をEmbedding APIへ渡し、検索に使えるベクトルか検証する。

        Args:
            query: ベクトル化する検索文1件。

        Returns:
            1536個の有限な浮動小数点数からなるタプル。

        Raises:
            ValueError: 返却件数が1件でない、次元数が違う、または数値が不正。
            AzureError: Azure認証に失敗した場合など。呼び出し元で変換する。
            OpenAIError: Embedding APIの呼び出し失敗。呼び出し元で変換する。
        """
        vectors: tuple[tuple[float, ...], ...] = await self._embedding_client.embed(
            [query]
        )
        if len(vectors) != 1:
            raise ValueError("Query embedding must contain exactly one vector")
        vector = vectors[0]
        if len(vector) != VECTOR_DIMENSIONS:
            raise ValueError(
                f"Query embedding must have {VECTOR_DIMENSIONS} dimensions"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            for value in vector
        ):
            raise ValueError("Query embedding must contain finite numbers")
        return tuple(float(value) for value in vector)

    @staticmethod
    def _build_filter(
        level: int | None, level_filter: Literal["at_most", "exact"] = "at_most"
    ) -> str:
        """公開・承認済みASVS 5.0.0に絞るOData条件を作る。通信は行わない。

        Args:
            level: 対象Levelの整数（1〜3）。NoneならLevel条件を追加しない。
            level_filter: at_mostは指定値以下、exactは指定値との一致を指定する。

        Returns:
            固定の対象条件と任意のLevel条件をandで結合したfilter文字列。

        Raises:
            ValueError: levelまたはlevel_filterが許容値でない場合。
        """
        conditions = [
            "framework_name eq 'OWASP ASVS'",
            "version eq '5.0.0'",
            "content_status eq 'approved'",
            "security_level eq 'public'",
        ]
        if level is not None:
            if type(level) is not int or level not in {1, 2, 3}:
                raise ValueError("level must be 1, 2, 3, or None")
            if level_filter == "at_most":
                conditions.append(f"level le {level}")
            elif level_filter == "exact":
                conditions.append(f"level eq {level}")
            else:
                raise ValueError("level_filter must be at_most or exact")
        return " and ".join(conditions)

    @staticmethod
    def _to_requirement_match(result: Mapping[str, Any]) -> RequirementMatch:
        """Azureの検索結果１件を検証し、ドメインモデルに変換する。

        Args:
            result: SELECT_FIELDSの11項目と@search.scoreを持つ検索結果。

        Returns:
            ASVS要件と有限の検索スコアを保持するRequirementMatch。

        Raises:
            KeyError: 必須フィールドが存在しない場合。
            ValueError: 文字列・Level・スコア、またはドメインの制約に違反する場合。
        """
        fields = {name: result[name] for name in SELECT_FIELDS}
        for name, value in fields.items():
            if name == "level":
                if type(value) is not int:
                    raise ValueError("Document level must be an integer")
            elif not isinstance(value, str) or not value.strip():
                raise ValueError(f"Document {name} must be a nonempty string")
        score = result["@search.score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not isfinite(score)
        ):
            raise ValueError("Search score must be a finite number")
        return RequirementMatch(AsvsRequirement(**fields), float(score))


def _log_search_event(
    event_logger: BoundLogger,
    stage: str,
    started: float,
    outcome: str,
    **details: Any,
) -> None:
    """Azure検索の成否と公開結果を構造化イベントとして出力する。

    Args:
        event_logger: 検索呼び出し単位のsearch_idをbindしたlogger。
        stage: embeddingまたはazure_search。
        started: 対象段階の開始時点のperf_counter値。
        outcome: successまたはfailure。failureはERROR、それ以外はINFOで記録する。
        **details: 件数・公開ASVS本文・エラー型など、呼び出し側で選別した情報。
            入力文、認証情報、例外本文は渡さない。

    Returns:
        None。appのログ設定に従って出力する。
    """
    event_details = {
        "stage": stage,
        "outcome": outcome,
        "duration_ms": round((perf_counter() - started) * 1000, 2),
        **details,
    }
    if outcome == "failure":
        event_logger.error("rag_search", **event_details)
    else:
        event_logger.info("rag_search", **event_details)
