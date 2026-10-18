import json
import os
import unittest
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

from azure.core.exceptions import HttpResponseError
from fastapi.testclient import TestClient
from openai import OpenAIError

from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.application.use_cases import SearchRequirements
from app.infrastructure.external.azure_search_requirement_repository import (
    SELECT_FIELDS,
    AzureSearchRequirementRepository,
)
from app.main import create_app
from app.presentation.api.api_dependencies import get_search_requirements

DOCUMENT = {
    "requirement_id": "V6.1.1",
    "chapter_id": "V6",
    "chapter_name_ja": "認証",
    "chapter_name_en": "Authentication",
    "section_id": "V6.1",
    "section_name_ja": "認証の文書化",
    "section_name_en": "Authentication Documentation",
    "description_ja": "認証要件を文書化する",
    "description_en": "Document authentication requirements",
    "level": 1,
    "version": "5.0.0",
    "@search.score": 0.85,
}


async def _items(*documents: dict[str, object]) -> AsyncIterator[dict[str, object]]:
    """テスト用のAzure検索結果を非同期に列挙する。

    Args:
        *documents: Azure検索結果として返す文書。

    Yields:
        指定順の検索結果文書。
    """
    for document in documents:
        yield document


class AzureRuntimeSearchTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """非同期Embedding・検索クライアントとrepositoryを初期化する。"""
        self.embedding = AsyncMock()
        self.embedding.embed.return_value = ((0.1,) * 1536,)
        self.search = AsyncMock()
        self.search.search.side_effect = lambda **_: _items(DOCUMENT.copy())
        self.repository = AzureSearchRequirementRepository(self.embedding, self.search)

    async def test_query_filters_and_domain_mapping(self) -> None:
        """非同期SDK呼び出しへ検索条件を渡し、結果をdomainへ変換することを確認する。"""
        matches = await self.repository.search("認証要件", level=2, limit=3)
        self.embedding.embed.assert_awaited_once_with(["認証要件"])
        args = self.search.search.call_args.kwargs
        self.assertIsNone(args["search_text"])
        self.assertEqual(args["top"], 3)
        self.assertEqual(args["vector_filter_mode"], "preFilter")
        self.assertEqual(args["select"], list(SELECT_FIELDS))
        self.assertIn("level le 2", args["filter"])
        self.assertEqual(matches[0].requirement.requirement_id, "V6.1.1")

    async def test_empty_results_and_paging_failure(self) -> None:
        """空結果と、非同期ページ取得中の失敗を適切に扱うことを確認する。"""
        self.search.search.side_effect = lambda **_: _items()
        self.assertEqual(
            await self.repository.search("認証要件", level=None, limit=3), ()
        )

        async def failed_pages() -> AsyncIterator[dict[str, object]]:
            """1件返した後にページ取得失敗を起こす反復子を返す。"""
            yield DOCUMENT
            raise HttpResponseError(message="private paging failure")

        self.search.search.side_effect = lambda **_: failed_pages()
        with self.assertRaises(RequirementSearchUnavailableError):
            await self.repository.search("認証要件", level=2, limit=3)

    async def test_sdk_errors_are_converted_without_calling_next_stage(self) -> None:
        """Embedding・検索のSDK例外を検索不能エラーへ変換することを確認する。"""
        self.embedding.embed.side_effect = OpenAIError("embedding failed")
        with self.assertRaises(RequirementSearchUnavailableError):
            await self.repository.search("private query", level=2, limit=3)
        self.search.search.assert_not_called()

        self.embedding.embed.side_effect = None
        self.search.search.side_effect = HttpResponseError(message="private details")
        with self.assertRaises(RequirementSearchUnavailableError):
            await self.repository.search("private query", level=2, limit=3)

    async def test_invalid_vectors_never_call_search(self) -> None:
        """不正なEmbeddingはAzure Searchを呼ばずに拒否することを確認する。"""
        self.embedding.embed.return_value = ((float("nan"),) * 1536,)
        with self.assertRaises(RequirementSearchUnavailableError):
            await self.repository.search("認証要件", level=2, limit=3)
        self.search.search.assert_not_called()

    async def test_incomplete_documents_and_invalid_configuration_return_failure(
        self,
    ) -> None:
        """不完全な文書と不正な検索設定を利用不能エラーへ変換することを確認する。"""
        for field in (*SELECT_FIELDS, "@search.score"):
            with self.subTest(field=field):
                document = DOCUMENT.copy()
                del document[field]
                self.search.search.side_effect = lambda document=document, **_: _items(
                    document
                )
                with self.assertRaises(RequirementSearchUnavailableError):
                    await self.repository.search("認証要件", level=2, limit=3)

        for backend in ("azure", "typo"):
            with self.subTest(backend=backend):
                get_search_requirements.cache_clear()
                self.addCleanup(get_search_requirements.cache_clear)
                with (
                    patch.dict(
                        os.environ, {"ASVS_SEARCH_BACKEND": backend}, clear=True
                    ),
                    TestClient(create_app()) as client,
                ):
                    response = client.post(
                        "/api/v1/requirements/search", json={"query": "認証要件"}
                    )
                self.assertEqual(response.status_code, 503)

    async def test_service_errors_preserve_status_and_private_details_are_not_logged(
        self,
    ) -> None:
        """各SDK障害の段階・HTTP状態を記録し、秘密情報をログに出さないことを確認する。"""
        for stage, client in (
            ("embedding", self.embedding.embed),
            ("azure_search", self.search.search),
        ):
            with self.subTest(stage=stage):
                error = HttpResponseError(message="secret credentials and query")
                error.status_code = 403
                client.side_effect = error
                with (
                    self.assertLogs("app", level="INFO") as captured,
                    self.assertRaises(RequirementSearchUnavailableError),
                ):
                    await self.repository.search("private query", level=2, limit=3)
                client.side_effect = None
                event = json.loads(captured.records[-1].getMessage())
                self.assertEqual(event["stage"], stage)
                self.assertEqual(event["http_status"], 403)
                self.assertNotIn("secret credentials", "".join(captured.output))
                self.assertNotIn("private query", "".join(captured.output))

    async def test_success_logs_do_not_include_query(self) -> None:
        """非同期検索の成功ログが相関IDを共有し、検索文を含まないことを確認する。"""
        with self.assertLogs("app", level="INFO") as captured:
            await self.repository.search("private query", level=2, limit=3)
        events = [json.loads(record.getMessage()) for record in captured.records]
        self.assertEqual(
            [event["stage"] for event in events], ["embedding", "azure_search"]
        )
        self.assertEqual(events[0]["search_id"], events[1]["search_id"])
        self.assertEqual(events[1]["level"], 2)
        self.assertEqual(events[1]["log_level"], "info")
        self.assertNotIn("private query", "".join(captured.output))

    async def test_azure_configuration_and_http_contract(self) -> None:
        """非同期Azureクライアントの構成と既存HTTP契約を確認する。"""
        env = {
            "ASVS_SEARCH_BACKEND": "azure",
            "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
            "AZURE_OPENAI_BASE_URL": "https://example.openai.azure.com/openai/v1/",
        }
        get_search_requirements.cache_clear()
        self.addCleanup(get_search_requirements.cache_clear)
        with (
            patch.dict(os.environ, env, clear=True),
            patch("azure.identity.aio.DefaultAzureCredential"),
            patch(
                "azure.search.documents.aio.SearchClient", return_value=self.search
            ) as factory,
            patch(
                "app.infrastructure.external.AsyncAzureOpenAIEmbeddingClient",
                return_value=self.embedding,
            ) as embed_factory,
            TestClient(create_app()) as client,
        ):
            response = client.post(
                "/api/v1/requirements/search", json={"query": "認証要件"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["requirement_id"], "V6.1.1")
        self.assertEqual(factory.call_args.kwargs["retry_total"], 0)
        self.assertEqual(embed_factory.call_args.kwargs["timeout_seconds"], 15.0)

    async def test_azure_logs_include_request_id_without_query_or_descriptions(
        self,
    ) -> None:
        """Azure検索ログが相関IDを記録し、入力文・要件本文を含まないことを確認する。"""
        application = create_app()
        application.dependency_overrides[get_search_requirements] = lambda: (
            SearchRequirements(self.repository)
        )
        self.addCleanup(application.dependency_overrides.clear)
        with (
            TestClient(application) as client,
            self.assertLogs("app", level="INFO") as captured,
        ):
            response = client.post(
                "/api/v1/requirements/search", json={"query": "private query"}
            )

        self.assertEqual(response.status_code, 200)
        events = [json.loads(record.getMessage()) for record in captured.records]
        azure_events = [event for event in events if event["event"] == "rag_search"]
        self.assertTrue(azure_events)
        self.assertTrue(
            all(
                event["request_id"] == response.headers["X-Request-ID"]
                for event in azure_events
            )
        )
        output = "".join(captured.output)
        self.assertNotIn("private query", output)
        self.assertNotIn(DOCUMENT["description_ja"], output)
        self.assertNotIn(DOCUMENT["description_en"], output)
