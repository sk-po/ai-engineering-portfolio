import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.settings import AnswerSettings, AzureSearchSettings, RuntimeSettings


class SettingsTestCase(unittest.TestCase):
    def test_runtime_settings_default_and_normalized_backend(self) -> None:
        """検索方式の既定値と空白・大文字を含む環境変数の正規化を確認する。"""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(RuntimeSettings().search_backend, "csv")

        with patch.dict(os.environ, {"ASVS_SEARCH_BACKEND": " AZURE "}, clear=True):
            self.assertEqual(RuntimeSettings().search_backend, "azure")

    def test_runtime_settings_rejects_unknown_backend(self) -> None:
        """未対応の検索方式を設定時の検証エラーとして拒否する。"""
        with (
            patch.dict(os.environ, {"ASVS_SEARCH_BACKEND": "unknown"}, clear=True),
            self.assertRaises(ValidationError),
        ):
            RuntimeSettings()

    def test_azure_settings_requires_urls_and_applies_defaults(self) -> None:
        """Azure接続URLを必須化し、IndexとDeploymentの既定値を適用する。"""
        env = {
            "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
            "AZURE_OPENAI_BASE_URL": ("https://example.openai.azure.com/openai/v1/"),
        }

        with patch.dict(os.environ, env, clear=True):
            settings = AzureSearchSettings()

        self.assertEqual(settings.search_index_name, "security-docs-v1")
        self.assertEqual(settings.embedding_deployment, "text-embedding-3-small")
        self.assertEqual(
            str(settings.openai_base_url),
            "https://example.openai.azure.com/openai/v1/",
        )

    def test_answer_settings_converts_limits_and_masks_api_key(self) -> None:
        """回答生成の数値変換とSecretStrによるAPIキーの秘匿を確認する。"""
        env = {
            "OPENAI_API_KEY": " private-test-api-key ",
            "OPENAI_CHAT_MODEL": " test-chat-model ",
            "OPENAI_CHAT_TIMEOUT_SECONDS": "12.5",
            "OPENAI_CHAT_MAX_COMPLETION_TOKENS": "640",
        }

        with patch.dict(os.environ, env, clear=True):
            settings = AnswerSettings()

        self.assertEqual(settings.api_key.get_secret_value(), "private-test-api-key")
        self.assertNotIn("private-test-api-key", repr(settings))
        self.assertEqual(settings.chat_model, "test-chat-model")
        self.assertEqual(settings.timeout_seconds, 12.5)
        self.assertEqual(settings.max_completion_tokens, 640)

    def test_answer_settings_rejects_blank_secret_and_nonpositive_limits(self) -> None:
        """空のAPIキーと0以下のtimeout・Token上限を拒否する。"""
        env = {
            "OPENAI_API_KEY": "   ",
            "OPENAI_CHAT_MODEL": "test-chat-model",
            "OPENAI_CHAT_TIMEOUT_SECONDS": "0",
            "OPENAI_CHAT_MAX_COMPLETION_TOKENS": "0",
        }

        with (
            patch.dict(os.environ, env, clear=True),
            self.assertRaises(ValidationError),
        ):
            AnswerSettings()

    def test_settings_do_not_load_dotenv_files_directly(self) -> None:
        """設定クラスが.envを直接読まず、コンテナ環境変数だけを使うことを確認する。"""
        self.assertIsNone(RuntimeSettings.model_config.get("env_file"))
        self.assertIsNone(AzureSearchSettings.model_config.get("env_file"))
        self.assertIsNone(AnswerSettings.model_config.get("env_file"))


if __name__ == "__main__":
    unittest.main()
