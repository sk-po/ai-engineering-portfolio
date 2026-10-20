from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.application.models import GuidedRequirementsResult
from app.presentation.api.schemas.asvs_schema import RequirementResponse
from app.presentation.api.schemas.asvs_v2_schema import LevelScopedRetrieval


class GuidedRequirementsTurnRequest(BaseModel):
    """ガイド付き要件探索の1ターンに必要なHTTP入力を検証する。"""

    feature_description: str = Field(min_length=20, max_length=1000)
    answers: list[str] = Field(default_factory=list, max_length=5)
    level: Literal[1, 2, 3] = 2

    @field_validator("feature_description")
    @classmethod
    def normalize_feature_description(cls, value: str) -> str:
        """対象機能の説明を空白除去して検証する。

        Args:
            value: 利用者が入力した機能説明。

        Returns:
            前後の空白を除去した機能説明。
        """
        return value.strip()


class GuidedRequirementsTurnResponse(BaseModel):
    action: Literal["ask", "complete"]
    question: str | None
    missing_topics: list[str]
    answer: str | None
    sources: list[RequirementResponse]
    retrieval: LevelScopedRetrieval | None
    turn: int

    @classmethod
    def from_application(
        cls, *, result: GuidedRequirementsResult, level: int
    ) -> "GuidedRequirementsTurnResponse":
        """ヒアリングユースケースの結果を公開APIレスポンスへ変換する。

        Args:
            result: 次の質問または最終回答を含むユースケース結果。
            level: 最終回答で使用したASVS最上位Level。

        Returns:
            画面が次の入力または最終根拠を表示できるレスポンス。
        """
        return cls(
            action=result.action,
            question=result.question,
            missing_topics=list(result.missing_topics),
            answer=result.answer,
            sources=[
                RequirementResponse.from_domain(source) for source in result.sources
            ],
            retrieval=(
                LevelScopedRetrieval.from_target_level(level)
                if result.action == "complete"
                else None
            ),
            turn=result.turn,
        )
