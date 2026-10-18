import unittest
from collections.abc import Sequence
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from app.application.models import AsvsIndexDocument, EmbeddedAsvsIndexDocument
from app.infrastructure.external.azure_openai_embedding_client import (
    AsyncAzureOpenAIEmbeddingClient,
    AzureOpenAIEmbeddingClient,
)
from app.infrastructure.external.azure_search_document_writer import (
    AzureSearchDocumentWriter,
)


def _document() -> AsvsIndexDocument:
    timestamp = datetime(2025, 5, 30, tzinfo=UTC)
    return AsvsIndexDocument(
        chunk_id="asvs-5-0-0-v1-1-1",
        document_id="asvs-5.0.0",
        title="title",
        section="section",
        content="content",
        source_uri="https://example.com",
        source_name="source",
        document_type="security-standard",
        category="application-security",
        tags=("ASVS",),
        language="ja-en",
        version="5.0.0",
        updated_at=timestamp,
        security_level="public",
        allowed_group_ids=(),
        security_domain="application",
        control_ids=("V1.1.1",),
        content_status="approved",
        effective_from=timestamp,
        framework_name="OWASP ASVS",
        requirement_id="V1.1.1",
        chapter_id="V1",
        chapter_name_ja="章",
        chapter_name_en="Chapter",
        section_id="V1.1",
        section_name_ja="節",
        section_name_en="Section",
        description_ja="要件",
        description_en="Requirement",
        level=2,
        translation_status="community-draft",
        official_english_source="https://example.com/en",
        japanese_translation_source="https://example.com/ja",
    )


class FakeEmbeddingsApi:
    def __init__(self) -> None:
        """Embedding APIへ渡された引数を記録するテストダブルを初期化する。"""
        self.arguments: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        """呼び出し引数を記録し、入力順と異なる固定応答を返す。

        Args:
            **kwargs: SDKのEmbedding生成メソッドへ渡された引数。

        Returns:
            indexとEmbeddingを持つ2件の固定応答。
        """
        self.arguments = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )


class FakeOpenAiClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsApi()


class FakeRateLimitError(Exception):
    def __init__(self) -> None:
        self.response = SimpleNamespace(headers={"retry-after": "0"})


class RateLimitedEmbeddingsApi(FakeEmbeddingsApi):
    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def create(self, **kwargs: Any) -> SimpleNamespace:
        """初回だけレート制限を発生させ、2回目以降は固定応答を返す。

        Args:
            **kwargs: SDKのEmbedding生成メソッドへ渡された引数。

        Returns:
            2回目以降の固定Embedding応答。

        Raises:
            FakeRateLimitError: 初回呼び出しの場合。
        """
        self.call_count += 1
        if self.call_count == 1:
            raise FakeRateLimitError()
        return super().create(**kwargs)


class FakeSearchClient:
    def __init__(self, *, succeeded: bool = True) -> None:
        """Azure Searchの登録成否を指定してテストダブルを初期化する。

        Args:
            succeeded: 各文書を登録成功として返すかどうか。
        """
        self.succeeded = succeeded
        self.documents: list[dict[str, object]] | None = None

    def merge_or_upload_documents(
        self, *, documents: Sequence[dict[str, object]]
    ) -> list[SimpleNamespace]:
        """登録文書を記録し、文書ごとの固定結果を返す。

        Args:
            documents: Azure Searchへ登録する文書列。

        Returns:
            文書キー、成否、エラー内容を持つ登録結果。
        """
        self.documents = list(documents)
        return [
            SimpleNamespace(
                key=document["chunk_id"],
                succeeded=self.succeeded,
                error_message=None if self.succeeded else "rejected",
            )
            for document in documents
        ]


class AzureIndexingAdaptersTestCase(unittest.TestCase):
    def test_embedding_client_preserves_input_order_by_response_index(self) -> None:
        sdk_client = FakeOpenAiClient()
        client = AzureOpenAIEmbeddingClient(
            base_url="https://example.openai.azure.com/openai/v1/",
            deployment_name="text-embedding-3-small",
            credential=object(),
            dimensions=2,
            sdk_client=sdk_client,
        )

        result = client.embed(["first", "second"])

        self.assertEqual(result, ((0.1, 0.2), (0.3, 0.4)))
        arguments = sdk_client.embeddings.arguments
        self.assertIsNotNone(arguments)
        assert arguments is not None
        self.assertEqual(arguments["dimensions"], 2)
        self.assertEqual(arguments["model"], "text-embedding-3-small")

    def test_embedding_client_waits_and_retries_rate_limit(self) -> None:
        sdk_client = FakeOpenAiClient()
        sdk_client.embeddings = RateLimitedEmbeddingsApi()
        waits: list[float] = []
        retry_notifications: list[tuple[int, float]] = []
        client = AzureOpenAIEmbeddingClient(
            base_url="https://example.openai.azure.com/openai/v1/",
            deployment_name="text-embedding-3-small",
            credential=object(),
            dimensions=2,
            sdk_client=sdk_client,
            rate_limit_error_type=FakeRateLimitError,
            rate_limit_buffer_seconds=0,
            sleep=waits.append,
            on_rate_limit=lambda attempt, seconds: retry_notifications.append(
                (attempt, seconds)
            ),
        )

        result = client.embed(["first", "second"])

        self.assertEqual(result, ((0.1, 0.2), (0.3, 0.4)))
        self.assertEqual(waits, [0.0])
        self.assertEqual(retry_notifications, [(1, 0.0)])

    def test_writer_serializes_collections_and_vector(self) -> None:
        sdk_client = FakeSearchClient()
        writer = AzureSearchDocumentWriter(
            endpoint="https://example.search.windows.net",
            index_name="security-docs-v1",
            credential=object(),
            sdk_client=sdk_client,
        )

        count = writer.merge_or_upload(
            [EmbeddedAsvsIndexDocument(_document(), (0.1, 0.2))]
        )

        self.assertEqual(count, 1)
        documents = sdk_client.documents
        self.assertIsNotNone(documents)
        assert documents is not None
        self.assertEqual(documents[0]["tags"], ["ASVS"])
        self.assertEqual(documents[0]["content_vector"], [0.1, 0.2])

    def test_runtime_embedding_does_not_wait_or_retry(self) -> None:
        sdk_client = FakeOpenAiClient()
        sdk_client.embeddings = RateLimitedEmbeddingsApi()
        waits: list[float] = []
        client = AzureOpenAIEmbeddingClient(
            base_url="https://example.openai.azure.com/openai/v1/",
            deployment_name="text-embedding-3-small",
            credential=object(),
            sdk_client=sdk_client,
            rate_limit_error_type=FakeRateLimitError,
            max_rate_limit_retries=0,
            sleep=waits.append,
        )
        with self.assertRaises(FakeRateLimitError):
            client.embed(["query"])
        self.assertEqual(sdk_client.embeddings.call_count, 1)
        self.assertEqual(waits, [])

    def test_writer_raises_for_partial_azure_failure(self) -> None:
        writer = AzureSearchDocumentWriter(
            endpoint="https://example.search.windows.net",
            index_name="security-docs-v1",
            credential=object(),
            sdk_client=FakeSearchClient(succeeded=False),
        )

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            writer.merge_or_upload([EmbeddedAsvsIndexDocument(_document(), (0.1, 0.2))])


class AsyncAzureEmbeddingClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_embed_awaits_sdk_and_preserves_input_order(self) -> None:
        """非同期SDKをawaitし、応答index順にEmbeddingを返すことを確認する。"""
        embeddings = AsyncMock()
        embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )
        sdk_client = SimpleNamespace(embeddings=embeddings, close=AsyncMock())
        client = AsyncAzureOpenAIEmbeddingClient(
            base_url="https://example.openai.azure.com/openai/v1/",
            deployment_name="text-embedding-3-small",
            credential=object(),
            dimensions=2,
            sdk_client=sdk_client,
        )

        result = await client.embed(["first", "second"])
        await client.close()

        self.assertEqual(result, ((0.1, 0.2), (0.3, 0.4)))
        embeddings.create.assert_awaited_once_with(
            model="text-embedding-3-small",
            input=["first", "second"],
            dimensions=2,
            encoding_format="float",
        )
        sdk_client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
