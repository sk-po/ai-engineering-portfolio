import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.infrastructure.external.openai_guided_requirements_planner_client import (
    OpenAIGuidedRequirementsPlannerClient,
    _fallback_decision,
)


def _sdk_client(content: str) -> SimpleNamespace:
    """指定した本文を返すChat Completions SDKのテストダブルを作成する。

    Args:
        content: モデルのmessage.contentとして返すJSON文字列。

    Returns:
        非同期createメソッドを持つSDK互換オブジェクト。
    """
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=content),
                )
            ]
        )
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


class OpenAIGuidedRequirementsPlannerClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_uses_fallback_question_when_model_omits_question(self) -> None:
        """質問本文がないモデル応答でも503にせず、固定質問を返すことを確認する。"""
        client = OpenAIGuidedRequirementsPlannerClient(
            api_key="test-api-key",
            model="test-chat-model",
            timeout_seconds=30,
            sdk_client=_sdk_client(
                '{"action":"ask","question":null,"missing_topics":[],"retrieval_queries":[]}'
            ),
        )

        decision = await client.plan("会員だけが口コミを編集できる機能です。", (), 2)

        self.assertEqual(decision.action, "ask")
        self.assertEqual(decision.missing_topics, ("認証と認可",))
        self.assertIsNotNone(decision.question)

    def test_completes_after_five_fallback_questions(self) -> None:
        """固定質問を5回済ませた後は、RAG回答へ進む判断になることを確認する。"""
        decision = _fallback_decision(5)

        self.assertEqual(decision.action, "complete")
        self.assertIsNone(decision.question)
