import unittest
from unittest.mock import AsyncMock, Mock

from app.application.models import (
    GeneratedRequirementAnswer,
    GuidedRequirementsDecision,
)
from app.application.use_cases import GenerateRequirementAnswer
from app.application.use_cases.guide_requirements_use_case import GuideRequirements


class GuideRequirementsTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """質問判断と既存RAG回答を非同期mockへ差し替えたユースケースを作成する。"""
        self.planner = Mock()
        self.planner.plan = AsyncMock()
        self.answer = Mock(spec=GenerateRequirementAnswer)
        self.answer.execute_per_level = AsyncMock()
        self.use_case = GuideRequirements(self.planner, self.answer)

    async def test_returns_the_next_question_without_running_rag(self) -> None:
        """未確認事項がある場合は質問だけを返すことを確認する。"""
        self.planner.plan.return_value = GuidedRequirementsDecision(
            action="ask",
            question="個人情報を扱いますか？",
            missing_topics=("扱うデータ",),
        )

        result = await self.use_case.execute(
            "利用者が会員登録し、メールアドレスを登録できる機能", answers=(), level=2
        )

        self.assertEqual(result.action, "ask")
        self.assertEqual(result.question, "個人情報を扱いますか？")
        self.answer.execute_per_level.assert_not_awaited()

    async def test_completes_with_level_scoped_rag_answer(self) -> None:
        """完了判断では既存のLevel別RAG回答を最終結果へ含めることを確認する。"""
        self.planner.plan.return_value = GuidedRequirementsDecision(
            action="complete", question=None, missing_topics=()
        )
        self.answer.execute_per_level.return_value = GeneratedRequirementAnswer(
            answer="設計で決めることを整理してください。", sources=()
        )

        result = await self.use_case.execute(
            "未ログイン利用者は口コミを3件まで閲覧でき、会員は全件を閲覧できる。"
            "投稿者だけが自分の口コミを編集・削除できる。",
            answers=(),
            level=2,
        )

        self.assertEqual(result.action, "complete")
        self.assertEqual(result.answer, "設計で決めることを整理してください。")
        self.answer.execute_per_level.assert_awaited_once_with(
            "以下の機能要件をセキュリティレビューしてください。\n"
            "未ログイン利用者は口コミを3件まで閲覧でき、会員は全件を閲覧できる。"
            "投稿者だけが自分の口コミを編集・削除できる。\n"
            "回答では、機能要件から確認すべき実装上のセキュリティ事項を示してください。\n"
            "根拠にない認証方式や機能を列挙しないでください。\n"
            "検索観点:\n"
            "認可 権限 アクセス制御 所有者 データ固有 機能レベル\n"
            "出力エンコーディング HTML インジェクション",
            target_level=2,
            search_query="認可 権限 アクセス制御 所有者 データ固有 機能レベル",
            response_style="security_review",
        )
