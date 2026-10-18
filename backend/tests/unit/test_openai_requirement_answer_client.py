import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.application.requirement_answer_errors import (
    RequirementAnswerUnavailableError,
)
from app.domain.models import AsvsRequirement, RequirementMatch
from app.infrastructure.external.openai_requirement_answer_client import (
    OpenAIRequirementAnswerClient,
)


def _match() -> RequirementMatch:
    """OpenAI生成clientテスト用のASVS検索結果を返す。

    Returns:
        日本語・英語本文を持つV6.1.1の検索結果。
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


def _sdk_client(
    *, content: str | None = "[V6.1.1]を確認してください。"
) -> SimpleNamespace:
    """指定本文を返す非同期Chat Completions SDK mockを生成する。

    Args:
        content: SDK応答のmessage.content。Noneは本文欠落を表す。

    Returns:
        chat.completions.createとcloseを持つSDK互換mock。
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
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        close=AsyncMock(),
    )


class OpenAIRequirementAnswerClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_sends_question_and_sources_and_returns_content(self) -> None:
        """質問と検索結果をメッセージへ含め、生成本文を返すことを確認する。"""
        sdk_client = _sdk_client()
        client = OpenAIRequirementAnswerClient(
            api_key="test-api-key",
            model="test-chat-model",
            max_completion_tokens=600,
            sdk_client=sdk_client,
        )

        with self.assertLogs("app", level="INFO") as captured:
            result = await client.generate("認証をどう設計する？", (_match(),))

        self.assertEqual(result, "[V6.1.1]を確認してください。")
        arguments = sdk_client.chat.completions.create.call_args.kwargs
        self.assertEqual(arguments["model"], "test-chat-model")
        self.assertEqual(arguments["messages"][0]["role"], "developer")
        self.assertEqual(arguments["max_completion_tokens"], 600)
        payload = json.loads(arguments["messages"][1]["content"])
        self.assertEqual(payload["question"], "認証をどう設計する？")
        self.assertEqual(payload["requirements"][0]["requirement_id"], "V6.1.1")
        self.assertEqual(
            payload["requirements"][0]["description_en"],
            "Document authentication requirements",
        )
        log_output = "".join(captured.output)
        self.assertNotIn("認証をどう設計する？", log_output)
        self.assertNotIn("認証要件を文書化する", log_output)
        self.assertNotIn("[V6.1.1]を確認してください。", log_output)

    async def test_rejects_invalid_response_without_logging_content(self) -> None:
        """本文欠落を安全なapplication例外へ変換し、入力をログへ出さない。"""
        sdk_client = _sdk_client(content=None)
        client = OpenAIRequirementAnswerClient(
            api_key="test-api-key",
            model="test-chat-model",
            sdk_client=sdk_client,
        )

        with (
            self.assertLogs("app", level="INFO") as captured,
            self.assertRaises(RequirementAnswerUnavailableError),
        ):
            await client.generate("private question", (_match(),))

        event = json.loads(captured.records[-1].getMessage())
        self.assertEqual(event["event"], "rag_generation")
        self.assertEqual(event["outcome"], "failure")
        self.assertNotIn("private question", "".join(captured.output))
        self.assertNotIn("認証要件を文書化する", "".join(captured.output))

    async def test_closes_sdk_client(self) -> None:
        """closeが非同期SDKの接続終了をawaitすることを確認する。"""
        sdk_client = _sdk_client()
        client = OpenAIRequirementAnswerClient(
            api_key="test-api-key",
            model="test-chat-model",
            sdk_client=sdk_client,
        )

        await client.close()

        sdk_client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
