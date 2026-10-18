from collections.abc import Sequence
from typing import Protocol

from app.application.models.guided_requirements_dto import GuidedRequirementsDecision


class GuidedRequirementsPlanner(Protocol):
    async def plan(
        self, feature_description: str, answers: Sequence[str], level: int
    ) -> GuidedRequirementsDecision:
        """機能説明と回答履歴から、次の質問または完了を判断する。

        Args:
            feature_description: 利用者が最初に記載した対象機能の説明。
            answers: これまでに利用者が回答した内容。順序を保持する。
            level: 検討対象のASVS最上位Level。

        Returns:
            次の操作、質問文、未確認の観点、RAG検索観点を持つ判断結果。
        """
        ...
