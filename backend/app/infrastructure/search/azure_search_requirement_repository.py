from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any, Protocol

from azure.core.exceptions import AzureError
from azure.search.documents.models import VectorizedQuery
from openai import OpenAIError

from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.application.ports.asvs_indexing_port import EmbeddingClient
from app.domain.models import AsvsRequirement, RequirementMatch

VECTOR_DIMENSIONS = 1536
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


class VectorSearchClient(Protocol):
    def search(
        self, search_text: str | None = None, **kwargs: Any
    ) -> Iterable[Mapping[str, Any]]:
        """Azure SDKとテスト用クライアントに共通する検索契約を定義する。

        Args:
            search_text: 全文検索用の文字列。Noneは全文検索を指定しない。
            **kwargs: ベクトル、filter、取得フィールド、件数などの検索条件。

        Returns:
            文書フィールドと検索スコアを持つ辞書の反復可能オブジェクト。
            実装によっては反復中にも外部通信が発生する。
        """
        ...


class AzureSearchRequirementRepository:
    """Embed a query, search approved ASVS vectors, and map the results."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        search_client: VectorSearchClient,
    ) -> None:
        """検索に必要なクライアントを受け取る。この時点では通信しない。

        Args:
            embedding_client: 登録文書と同じモデルで文章をベクトル化するクライアント。
            search_client: 対象Indexへ検索要求を送るクライアント。
        """
        self._embedding_client = embedding_client
        self._search_client = search_client

    def search(
        self, query: str, *, level: int | None, limit: int
    ) -> tuple[RequirementMatch, ...]:
        """検索文をベクトル化し、公開・承認済みASVS要件をAzureで検索する。

        Args:
            query: ユースケースで空白除去・検証済みの検索文。
            level: 対象Levelの上限（1〜3）。NoneならLevelで制限しない。
            limit: 最大取得件数。ユースケースで1〜10に検証済みであること。

        Returns:
            Azureの返却順を保持した検索結果のタプル。該当なしは空タプル。

        Raises:
            RequirementSearchUnavailableError: SDKの通信・認証エラー、または
                ベクトルや検索結果の検証失敗。ページ取得中の失敗も含む。

        Notes:
            Embedding APIとAzure AI Searchへ通信する。CSVへの自動切り替えは行わない。
        """
        try:
            query_vector = self._embed_query(query)
            results = self._search_client.search(
                search_text=None,
                vector_queries=[
                    VectorizedQuery(
                        vector=list(query_vector),
                        k_nearest_neighbors=limit,
                        fields=VECTOR_FIELD,
                        exhaustive=False,
                    )
                ],
                filter=self._build_filter(level),
                vector_filter_mode="preFilter",
                select=list(SELECT_FIELDS),
                top=limit,
            )
            # SearchItemPaged performs I/O during iteration as well as search().
            return tuple(self._to_requirement_match(result) for result in results)
        except (AzureError, OpenAIError, ValueError, TypeError, KeyError) as error:
            raise RequirementSearchUnavailableError(
                "Requirement search is temporarily unavailable"
            ) from error

    def _embed_query(self, query: str) -> tuple[float, ...]:
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
        vectors = self._embedding_client.embed([query])
        if len(vectors) != 1:
            raise ValueError("Query embedding must contain exactly one vector")
        vector = vectors[0]
        if len(vector) != VECTOR_DIMENSIONS:
            raise ValueError(f"Query embedding must have {VECTOR_DIMENSIONS} dimensions")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            for value in vector
        ):
            raise ValueError("Query embedding must contain finite numbers")
        return tuple(float(value) for value in vector)

    @staticmethod
    def _build_filter(level: int | None) -> str:
        """公開・承認済みASVS 5.0.0に絞るOData条件を作る。通信は行わない。

        Args:
            level: Level上限の整数（1〜3）。NoneならLevel条件を追加しない。

        Returns:
            固定の対象条件と任意のLevel条件をandで結合したfilter文字列。

        Raises:
            ValueError: levelがNoneでも1〜3の整数でもない場合。
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
            conditions.append(f"level le {level}")
        return " and ".join(conditions)

    @staticmethod
    def _to_requirement_match(result: Mapping[str, Any]) -> RequirementMatch:
        """Azureの検索結果1件を検証し、ドメインモデルに変換する。

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
