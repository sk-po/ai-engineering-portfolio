from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from app.application.models import EmbeddedAsvsIndexDocument


class AzureSearchDocumentWriter:
    def __init__(
        self,
        *,
        endpoint: str,
        index_name: str,
        credential: Any,
        sdk_client: Any | None = None,
    ) -> None:
        if not endpoint.strip():
            raise ValueError("endpoint is required")
        if not index_name.strip():
            raise ValueError("index_name is required")
        if sdk_client is None:
            from azure.search.documents import SearchClient

            sdk_client = SearchClient(
                endpoint=endpoint.rstrip("/"),
                index_name=index_name,
                credential=credential,
            )
        self._client = sdk_client

    def merge_or_upload(self, documents: Sequence[EmbeddedAsvsIndexDocument]) -> int:
        if not documents:
            return 0
        payloads = [_to_payload(document) for document in documents]
        results = self._client.merge_or_upload_documents(documents=payloads)
        failures = [result for result in results if not result.succeeded]
        if failures:
            details = "; ".join(
                f"{result.key}: {result.error_message or 'unknown error'}"
                for result in failures
            )
            raise RuntimeError(f"Azure AI Search rejected documents: {details}")
        return len(results)


def _to_payload(document: EmbeddedAsvsIndexDocument) -> dict[str, object]:
    payload: dict[str, object] = asdict(document.document)
    for key, value in tuple(payload.items()):
        if isinstance(value, tuple):
            payload[key] = list(value)
    payload["content_vector"] = list(document.content_vector)
    return payload
