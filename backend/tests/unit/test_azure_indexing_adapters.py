import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from app.application.models import AsvsIndexDocument, EmbeddedAsvsIndexDocument
from app.infrastructure.embeddings.azure_openai_embedding_client import (
    AzureOpenAIEmbeddingClient,
)
from app.infrastructure.search.azure_search_document_writer import (
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
        self.arguments = None

    def create(self, **kwargs):
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

    def create(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            raise FakeRateLimitError()
        return super().create(**kwargs)


class FakeSearchClient:
    def __init__(self, *, succeeded: bool = True) -> None:
        self.succeeded = succeeded
        self.documents = None

    def merge_or_upload_documents(self, *, documents):
        self.documents = documents
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
        self.assertEqual(sdk_client.embeddings.arguments["dimensions"], 2)
        self.assertEqual(
            sdk_client.embeddings.arguments["model"], "text-embedding-3-small"
        )

    def test_embedding_client_waits_and_retries_rate_limit(self) -> None:
        sdk_client = FakeOpenAiClient()
        sdk_client.embeddings = RateLimitedEmbeddingsApi()
        waits = []
        retry_notifications = []
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
        self.assertEqual(sdk_client.documents[0]["tags"], ["ASVS"])
        self.assertEqual(sdk_client.documents[0]["content_vector"], [0.1, 0.2])

    def test_writer_raises_for_partial_azure_failure(self) -> None:
        writer = AzureSearchDocumentWriter(
            endpoint="https://example.search.windows.net",
            index_name="security-docs-v1",
            credential=object(),
            sdk_client=FakeSearchClient(succeeded=False),
        )

        with self.assertRaisesRegex(RuntimeError, "rejected"):
            writer.merge_or_upload(
                [EmbeddedAsvsIndexDocument(_document(), (0.1, 0.2))]
            )


if __name__ == "__main__":
    unittest.main()
