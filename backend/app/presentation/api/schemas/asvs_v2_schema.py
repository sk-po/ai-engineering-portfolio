from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.application.models import GeneratedRequirementAnswer
from app.presentation.api.schemas.asvs_schema import (
    JAPANESE_DRAFT_SOURCE,
    OFFICIAL_ENGLISH_SOURCE,
    TRANSLATION_NOTICE,
    RequirementResponse,
)

RETRIEVAL_LIMIT_PER_LEVEL = 5


class LevelScopedRequirementRequest(BaseModel):
    """Level別RAG検索に使用するHTTP入力を検証する。"""

    query: str = Field(min_length=2, max_length=200)
    level: Literal[1, 2, 3] = 2

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        """検索文の前後の空白を除去し、有効な長さか検証する。

        Args:
            value: Pydanticのフィールド検証を通過した検索文字列。

        Returns:
            前後の空白を除いた検索文字列。

        Raises:
            ValueError: 空白除去後に2文字未満となる場合。
        """
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("query must contain at least two characters")
        return normalized


class LevelScopedRetrieval(BaseModel):
    """Level別に実行したRAG検索の条件を表す。"""

    levels_searched: list[int]
    limit_per_level: int = RETRIEVAL_LIMIT_PER_LEVEL

    @classmethod
    def from_target_level(cls, target_level: int) -> "LevelScopedRetrieval":
        """選択された最上位Levelから実行済みLevel一覧を作る。

        Args:
            target_level: L1からこのLevelまでを検索する最上位Level。

        Returns:
            実行済みLevelと各Levelの最大取得件数を持つメタデータ。
        """
        return cls(levels_searched=list(range(1, target_level + 1)))


class LevelScopedSearchResponse(BaseModel):
    query: str
    level: int
    retrieval: LevelScopedRetrieval
    results: list[RequirementResponse]
    translation_notice: str = TRANSLATION_NOTICE
    official_english_source: str = OFFICIAL_ENGLISH_SOURCE
    japanese_draft_source: str = JAPANESE_DRAFT_SOURCE


class LevelScopedAnswerResponse(BaseModel):
    query: str
    level: int
    retrieval: LevelScopedRetrieval
    answer: str
    sources: list[RequirementResponse]
    translation_notice: str = TRANSLATION_NOTICE
    official_english_source: str = OFFICIAL_ENGLISH_SOURCE
    japanese_draft_source: str = JAPANESE_DRAFT_SOURCE

    @classmethod
    def from_application(
        cls,
        *,
        query: str,
        level: int,
        result: GeneratedRequirementAnswer,
    ) -> "LevelScopedAnswerResponse":
        """Level別検索を使った生成結果をv2の公開レスポンスへ変換する。

        Args:
            query: 入力検証済みの利用者の質問。
            level: 検索した最上位Level。
            result: 生成回答と、Levelごとに検索した根拠要件。

        Returns:
            回答、根拠要件、抽出条件、翻訳上の注意と出典を含むレスポンス。
        """
        return cls(
            query=query,
            level=level,
            retrieval=LevelScopedRetrieval.from_target_level(level),
            answer=result.answer,
            sources=[
                RequirementResponse.from_domain(source) for source in result.sources
            ],
        )
