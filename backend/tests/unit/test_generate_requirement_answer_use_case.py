import unittest
from unittest.mock import AsyncMock, Mock

from app.application.use_cases import GenerateRequirementAnswer, SearchRequirements
from app.application.use_cases.generate_requirement_answer_use_case import (
    NO_RELEVANT_REQUIREMENTS_ANSWER,
)
from app.domain.models import AsvsRequirement, RequirementMatch


def _match() -> RequirementMatch:
    """回答生成テストで使用するASVS検索結果を返す。

    Returns:
        V6.1.1を表す固定の検索結果。
    """
    return RequirementMatch(
        requirement=AsvsRequirement(
            requirement_id="V6.1.1",
            chapter_id="V6",
            chapter_name_ja="認証",
            chapter_name_en="Authentication",
            section_id="V6.1",
            section_name_ja="認証の文書化",
            section_name_en="Authentication Documentation",
            description_ja="認証要件を文書化する",
            description_en="Document authentication requirements",
            level=1,
        ),
        score=0.85,
    )


class GenerateRequirementAnswerTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """検索と生成を非同期mockへ差し替えたユースケースを作成する。"""
        self.search = Mock(spec=SearchRequirements)
        self.search.execute = AsyncMock()
        self.generator = Mock()
        self.generator.generate = AsyncMock()
        self.use_case = GenerateRequirementAnswer(self.search, self.generator)

    async def test_generates_from_retrieved_requirements(self) -> None:
        """検索結果を変更せず生成portへ渡し、回答と根拠を返すことを確認する。"""
        match = _match()
        self.search.execute.return_value = (match,)
        self.generator.generate.return_value = "[V6.1.1]を確認してください。"

        result = await self.use_case.execute("  認証要件  ", level=2, limit=3)

        self.search.execute.assert_awaited_once_with("  認証要件  ", level=2, limit=3)
        self.generator.generate.assert_awaited_once_with("認証要件", (match,))
        self.assertEqual(result.answer, "[V6.1.1]を確認してください。")
        self.assertEqual(result.sources, (match,))

    async def test_does_not_generate_without_retrieved_requirements(self) -> None:
        """検索結果が空なら外部生成を呼ばず、根拠不足の固定回答を返す。"""
        self.search.execute.return_value = ()

        result = await self.use_case.execute("認証要件")

        self.generator.generate.assert_not_awaited()
        self.assertEqual(result.answer, NO_RELEVANT_REQUIREMENTS_ANSWER)
        self.assertEqual(result.sources, ())

    async def test_uses_focused_search_query_and_original_review_context(self) -> None:
        """検索語を短くしても、生成には元のレビュー文を渡すことを確認する。"""
        match = _match()
        self.search.execute_per_level = AsyncMock(return_value=(match,))
        self.generator.generate.return_value = "認可を確認してください。"

        result = await self.use_case.execute_per_level(
            "口コミの閲覧と編集・削除をレビューしてください。",
            target_level=2,
            search_query="認可 所有者 データ固有",
        )

        self.search.execute_per_level.assert_awaited_once_with(
            "認可 所有者 データ固有", target_level=2, limit_per_level=5
        )
        self.generator.generate.assert_awaited_once_with(
            "口コミの閲覧と編集・削除をレビューしてください。", (match,)
        )
        self.assertEqual(result.answer, "認可を確認してください。")


if __name__ == "__main__":
    unittest.main()
