import json
import os
import unittest
from typing import ClassVar
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.application.application_errors import ApplicationError
from app.application.models import GeneratedRequirementAnswer
from app.application.requirement_answer_errors import RequirementAnswerUnavailableError
from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.application.use_cases import GenerateRequirementAnswer
from app.domain.models import AsvsRequirement, RequirementMatch
from app.main import app, create_app
from app.presentation.api.api_dependencies import get_generate_requirement_answer


class ApiTestCase(unittest.TestCase):
    client: ClassVar[TestClient]

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_root_returns_hello_world(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, World!"})

    def test_say_hello_uses_name(self) -> None:
        response = self.client.get("/hello/world")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, world!"})

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_registers_one_handler_for_application_error_hierarchy(self) -> None:
        """個別application例外を共通基底のhandlerで捕捉することを確認する。"""
        application = create_app()

        self.assertTrue(issubclass(RequirementSearchUnavailableError, ApplicationError))
        self.assertTrue(issubclass(RequirementAnswerUnavailableError, ApplicationError))
        self.assertIn(ApplicationError, application.exception_handlers)
        self.assertNotIn(
            RequirementSearchUnavailableError, application.exception_handlers
        )
        self.assertNotIn(
            RequirementAnswerUnavailableError, application.exception_handlers
        )

    def test_searches_asvs_requirements_in_japanese(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "パスワードの安全な保存", "level": 2, "limit": 3},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["query"], "パスワードの安全な保存")
        self.assertLessEqual(len(body["results"]), 3)
        self.assertGreater(len(body["results"]), 0)
        self.assertEqual(body["results"][0]["requirement_id"], "V11.4.2")
        self.assertTrue(body["results"][0]["description_ja"])
        self.assertIn("邦訳ドラフト", body["translation_notice"])

    def test_finds_an_exact_requirement_id(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "V6.1.1", "level": None, "limit": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["requirement_id"], "V6.1.1")

    def test_v2_searches_each_level_separately(self) -> None:
        """v2がL1から選択Levelまでを各5件の完全一致Level検索で結合することを確認する。"""
        response = self.client.post(
            "/api/v2/requirements/search",
            json={"query": "認証", "level": 3},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            body["retrieval"],
            {"levels_searched": [1, 2, 3], "limit_per_level": 5},
        )
        self.assertLessEqual(len(body["results"]), 15)
        for level in (1, 2, 3):
            level_results = [item for item in body["results"] if item["level"] == level]
            self.assertLessEqual(len(level_results), 5)

    def test_generates_answer_with_retrieved_sources(self) -> None:
        """生成回答APIが回答とモデルへ渡した根拠要件を返すことを確認する。"""
        match = RequirementMatch(
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
        use_case = Mock(spec=GenerateRequirementAnswer)
        use_case.execute = AsyncMock(
            return_value=GeneratedRequirementAnswer(
                answer="[V6.1.1] 認証要件を文書化してください。",
                sources=(match,),
            )
        )
        application = create_app()
        application.dependency_overrides[get_generate_requirement_answer] = lambda: (
            use_case
        )

        with TestClient(application) as client:
            response = client.post(
                "/api/v1/requirements/answer",
                json={"query": "認証をどう設計する？", "level": 2, "limit": 5},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "[V6.1.1] 認証要件を文書化してください。")
        self.assertEqual(body["sources"][0]["requirement_id"], "V6.1.1")
        self.assertIn("邦訳ドラフト", body["translation_notice"])
        use_case.execute.assert_awaited_once_with(
            "認証をどう設計する？", level=2, limit=5
        )

    def test_v2_generates_answer_from_level_scoped_sources(self) -> None:
        """v2回答APIがLevel別検索の根拠と抽出条件を返すことを確認する。"""
        match = RequirementMatch(
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
        use_case = Mock(spec=GenerateRequirementAnswer)
        use_case.execute_per_level = AsyncMock(
            return_value=GeneratedRequirementAnswer(
                answer="[V6.1.1] 回答", sources=(match,)
            )
        )
        application = create_app()
        application.dependency_overrides[get_generate_requirement_answer] = lambda: (
            use_case
        )

        with TestClient(application) as client:
            response = client.post(
                "/api/v2/requirements/answer",
                json={"query": "認証をどう設計する？", "level": 2},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["sources"][0]["requirement_id"], "V6.1.1")
        self.assertEqual(
            body["retrieval"],
            {"levels_searched": [1, 2], "limit_per_level": 5},
        )
        use_case.execute_per_level.assert_awaited_once_with(
            "認証をどう設計する？", target_level=2, limit_per_level=5
        )

    def test_returns_safe_503_when_answer_configuration_is_missing(self) -> None:
        """生成設定がなければ内部設定名を公開せず503と相関IDを返す。"""
        get_generate_requirement_answer.cache_clear()
        self.addCleanup(get_generate_requirement_answer.cache_clear)

        with patch.dict(os.environ, {}, clear=True), TestClient(create_app()) as client:
            response = client.post(
                "/api/v1/requirements/answer",
                json={"query": "認証をどう設計する？"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "Requirement answer generation is temporarily unavailable"},
        )
        self.assertEqual(len(response.headers["X-Request-ID"]), 32)

    def test_builds_answer_use_case_from_openai_configuration(self) -> None:
        """OpenAI用の環境変数を生成clientの設定へ渡すことを確認する。"""
        get_generate_requirement_answer.cache_clear()
        self.addCleanup(get_generate_requirement_answer.cache_clear)
        env = {
            "OPENAI_API_KEY": "private-test-api-key",
            "OPENAI_CHAT_MODEL": "test-chat-model",
            "OPENAI_CHAT_TIMEOUT_SECONDS": "12.5",
            "OPENAI_CHAT_MAX_COMPLETION_TOKENS": "640",
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "app.infrastructure.external.OpenAIRequirementAnswerClient"
            ) as factory,
        ):
            use_case = get_generate_requirement_answer()

        self.assertIsInstance(use_case, GenerateRequirementAnswer)
        factory.assert_called_once_with(
            api_key="private-test-api-key",
            model="test-chat-model",
            timeout_seconds=12.5,
            max_completion_tokens=640,
        )

    def test_rejects_a_blank_search_query(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "  "},
        )

        self.assertEqual(response.status_code, 422)

    def test_adds_request_id_and_does_not_log_search_query(self) -> None:
        """成功した要求に相関IDを付与し、検索文を構造化ログへ出さないことを確認する。"""
        query = "利用者入力として秘匿する検索文"
        with self.assertLogs("app", level="INFO") as captured:
            response = self.client.post(
                "/api/v1/requirements/search",
                json={"query": query},
            )

        self.assertEqual(response.status_code, 200)
        request_id = response.headers["X-Request-ID"]
        self.assertEqual(len(request_id), 32)
        events = [json.loads(record.getMessage()) for record in captured.records]
        access_log = next(
            event for event in events if event["event"] == "http_request.completed"
        )
        self.assertEqual(access_log["request_id"], request_id)
        self.assertEqual(access_log["path_template"], "/api/v1/requirements/search")
        self.assertEqual(access_log["log_level"], "info")
        self.assertNotIn(query, "".join(captured.output))

    def test_logs_validation_failure_without_request_body(self) -> None:
        """422では入力本文を出さず、相関ID付きの検証失敗イベントを記録する。"""
        query = "  "
        with self.assertLogs("app", level="INFO") as captured:
            response = self.client.post(
                "/api/v1/requirements/search",
                json={"query": query},
            )

        self.assertEqual(response.status_code, 422)
        event = next(
            json.loads(record.getMessage())
            for record in captured.records
            if json.loads(record.getMessage())["event"]
            == "http_request.validation_failed"
        )
        self.assertEqual(event["status_code"], 422)
        self.assertEqual(event["request_id"], response.headers["X-Request-ID"])
        self.assertNotIn(query, "".join(captured.output))

    def test_returns_safe_500_with_request_id_for_unexpected_error(self) -> None:
        """未分類例外では内部詳細を返さず、相関ID付きの例外ログを出すことを確認する。"""
        application = create_app()

        @application.get("/unexpected-error")
        async def unexpected_error() -> None:
            """テスト用に秘密文字列を含む未分類例外を発生させる。"""
            raise RuntimeError("secret implementation detail")

        with (
            TestClient(application, raise_server_exceptions=False) as client,
            self.assertLogs("app", level="INFO") as captured,
        ):
            response = client.get("/unexpected-error")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error"})
        event = next(
            json.loads(record.getMessage())
            for record in captured.records
            if json.loads(record.getMessage())["event"] == "http_exception.unexpected"
        )
        self.assertEqual(event["request_id"], response.headers["X-Request-ID"])
        self.assertEqual(event["error_type"], "RuntimeError")
        self.assertNotIn("secret implementation detail", "".join(captured.output))
        self.assertEqual(
            sum(
                json.loads(record.getMessage())["event"] == "http_exception.unexpected"
                for record in captured.records
            ),
            1,
        )
        self.assertFalse(
            any(
                json.loads(record.getMessage())["event"] == "http_request.failed"
                for record in captured.records
            )
        )


if __name__ == "__main__":
    unittest.main()
