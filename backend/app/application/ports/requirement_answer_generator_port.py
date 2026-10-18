from collections.abc import Sequence
from typing import Literal, Protocol

from app.domain.models import RequirementMatch


class RequirementAnswerGenerator(Protocol):
    async def generate(
        self,
        query: str,
        sources: Sequence[RequirementMatch],
        *,
        response_style: Literal["standard", "security_review"] = "standard",
    ) -> str:
        """質問と検索済みASVS要件から、根拠付き回答を生成する。

        Args:
            query: 入力検証・正規化済みの利用者の質問。
            sources: 回答で参照できるASVS要件。空ではないこと。
            response_style: standardは通常検索、security_reviewは具体的な機能要件の
                レビュー用の回答方針を適用する。既定はstandard。

        Returns:
            根拠要件のIDを示す、空でない回答文。

        Raises:
            RequirementAnswerUnavailableError: 外部生成サービスを利用できない場合。
        """
        ...
