from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.application.models import GeneratedRequirementAnswer
from app.domain.models.asvs_requirement_model import RequirementMatch

OFFICIAL_ENGLISH_SOURCE = "https://github.com/OWASP/ASVS/tree/v5.0.0"
JAPANESE_DRAFT_SOURCE = "https://github.com/owasp-ja/asvs-ja/tree/master/5.0"
TRANSLATION_NOTICE = (
    "日本語はコミュニティ邦訳ドラフトです。正式な解釈は英語原文を確認してください。"
)


class RequirementSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    level: Literal[1, 2, 3] | None = 2
    limit: int = Field(default=5, ge=1, le=10)

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


class RequirementResponse(BaseModel):
    requirement_id: str
    chapter_id: str
    chapter_name_ja: str
    chapter_name_en: str
    section_id: str
    section_name_ja: str
    section_name_en: str
    description_ja: str
    description_en: str
    level: int
    version: str
    score: float

    @classmethod
    def from_domain(cls, match: RequirementMatch) -> "RequirementResponse":
        """ドメインの検索結果をAPIの公開レスポンスへ変換する。

        Args:
            match: ASVS要件と検索スコアを保持するドメインモデル。

        Returns:
            要件の11項目とscoreを持つレスポンスモデル。
        """
        requirement = match.requirement
        return cls(
            requirement_id=requirement.requirement_id,
            chapter_id=requirement.chapter_id,
            chapter_name_ja=requirement.chapter_name_ja,
            chapter_name_en=requirement.chapter_name_en,
            section_id=requirement.section_id,
            section_name_ja=requirement.section_name_ja,
            section_name_en=requirement.section_name_en,
            description_ja=requirement.description_ja,
            description_en=requirement.description_en,
            level=requirement.level,
            version=requirement.version,
            score=match.score,
        )


class RequirementSearchResponse(BaseModel):
    query: str
    level: int | None
    results: list[RequirementResponse]
    translation_notice: str = TRANSLATION_NOTICE
    official_english_source: str = OFFICIAL_ENGLISH_SOURCE
    japanese_draft_source: str = JAPANESE_DRAFT_SOURCE


class RequirementAnswerRequest(RequirementSearchRequest):
    pass


class RequirementAnswerResponse(BaseModel):
    query: str
    level: int | None
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
        level: int | None,
        result: GeneratedRequirementAnswer,
    ) -> "RequirementAnswerResponse":
        """生成ユースケースの結果を公開APIレスポンスへ変換する。

        Args:
            query: 入力検証済みの利用者の質問。
            level: 検索に使用したLevel上限。Noneは全Levelを表す。
            result: 生成回答と、その根拠になったASVS検索結果。

        Returns:
            回答、根拠要件、翻訳上の注意と出典を含むレスポンス。
        """
        return cls(
            query=query,
            level=level,
            answer=result.answer,
            sources=[
                RequirementResponse.from_domain(source) for source in result.sources
            ],
        )
