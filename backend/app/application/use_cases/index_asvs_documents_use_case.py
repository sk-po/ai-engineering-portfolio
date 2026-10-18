import re
from collections.abc import Callable
from datetime import UTC, datetime

from app.application.models import (
    AsvsIndexDocument,
    EmbeddedAsvsIndexDocument,
    IndexingSummary,
)
from app.application.ports.asvs_indexing_port import (
    AsvsRequirementSource,
    EmbeddingClient,
    SearchDocumentWriter,
)
from app.domain.models import AsvsRequirement

_SEARCH_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_=-]*$")
_ASVS_RELEASED_AT = datetime(2025, 5, 30, tzinfo=UTC)
_OFFICIAL_SOURCE = "https://github.com/OWASP/ASVS/tree/v5.0.0"
_JAPANESE_SOURCE = "https://github.com/owasp-ja/asvs-ja/tree/master/5.0"

"""
Index登録用処理のUseCase
"""


class IndexAsvsDocuments:
    def __init__(
        self,
        source: AsvsRequirementSource,
        embedding_client: EmbeddingClient | None = None,
        document_writer: SearchDocumentWriter | None = None,
        *,
        vector_dimensions: int = 1536,
        batch_size: int = 16,
        expected_source_count: int = 345,
        on_batch_completed: Callable[[int, int, int], None] | None = None,
    ) -> None:
        if vector_dimensions < 1:
            raise ValueError("vector_dimensions must be positive")
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        self._source = source
        self._embedding_client = embedding_client
        self._document_writer = document_writer
        self._vector_dimensions = vector_dimensions
        self._batch_size = batch_size
        self._expected_source_count = expected_source_count
        self._on_batch_completed = on_batch_completed

    def prepare(self, *, limit: int | None = None) -> tuple[AsvsIndexDocument, ...]:
        requirements = self._source.list_all()
        self._validate_source(requirements)
        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be positive")
            requirements = requirements[:limit]

        documents = tuple(_to_index_document(item) for item in requirements)
        chunk_ids = {document.chunk_id for document in documents}
        if len(chunk_ids) != len(documents):
            raise ValueError("Generated chunk IDs are not unique")
        return documents

    def execute(self, *, limit: int | None = None) -> IndexingSummary:
        if self._embedding_client is None or self._document_writer is None:
            raise RuntimeError("Embedding client and document writer are required")

        documents = self.prepare(limit=limit)
        indexed_count = 0
        batch_count = 0
        for offset in range(0, len(documents), self._batch_size):
            batch = documents[offset : offset + self._batch_size]
            vectors = self._embedding_client.embed(
                [document.content for document in batch]
            )
            if len(vectors) != len(batch):
                raise ValueError("Embedding result count does not match input count")
            for vector in vectors:
                if len(vector) != self._vector_dimensions:
                    raise ValueError(
                        "Embedding dimensions do not match the index schema: "
                        f"expected {self._vector_dimensions}, got {len(vector)}"
                    )

            embedded = tuple(
                EmbeddedAsvsIndexDocument(document, vector)
                for document, vector in zip(batch, vectors, strict=True)
            )
            written = self._document_writer.merge_or_upload(embedded)
            if written != len(batch):
                raise RuntimeError(
                    f"Document writer reported {written}/{len(batch)} successful writes"
                )
            indexed_count += written
            batch_count += 1
            if self._on_batch_completed is not None:
                self._on_batch_completed(batch_count, indexed_count, len(documents))

        return IndexingSummary(
            source_count=len(documents),
            indexed_count=indexed_count,
            batch_count=batch_count,
        )

    def _validate_source(self, requirements: tuple[AsvsRequirement, ...]) -> None:
        if len(requirements) != self._expected_source_count:
            raise ValueError(
                "Unexpected ASVS source count: "
                f"expected {self._expected_source_count}, got {len(requirements)}"
            )
        requirement_ids = {item.requirement_id for item in requirements}
        if len(requirement_ids) != len(requirements):
            raise ValueError("ASVS source contains duplicate requirement IDs")


def _to_index_document(requirement: AsvsRequirement) -> AsvsIndexDocument:
    chunk_id = _search_key(f"asvs-{requirement.version}-{requirement.requirement_id}")
    content = "\n".join(
        (
            f"Requirement ID: {requirement.requirement_id}",
            f"Chapter: {requirement.chapter_id} {requirement.chapter_name_ja} / "
            f"{requirement.chapter_name_en}",
            f"Section: {requirement.section_id} {requirement.section_name_ja} / "
            f"{requirement.section_name_en}",
            f"Level: L{requirement.level}",
            f"Japanese: {requirement.description_ja}",
            f"English: {requirement.description_en}",
        )
    )
    return AsvsIndexDocument(
        chunk_id=chunk_id,
        document_id=f"asvs-{requirement.version}",
        title=f"{requirement.requirement_id} {requirement.section_name_ja}",
        section=f"{requirement.section_id} {requirement.section_name_ja}",
        content=content,
        source_uri=_OFFICIAL_SOURCE,
        source_name=f"OWASP ASVS {requirement.version}",
        document_type="security-standard",
        category="application-security",
        tags=(
            "OWASP",
            "ASVS",
            requirement.chapter_id,
            requirement.section_id,
            requirement.requirement_id,
        ),
        language="ja-en",
        version=requirement.version,
        updated_at=_ASVS_RELEASED_AT,
        security_level="public",
        allowed_group_ids=(),
        security_domain="application",
        control_ids=(requirement.requirement_id,),
        content_status="approved",
        effective_from=_ASVS_RELEASED_AT,
        framework_name="OWASP ASVS",
        requirement_id=requirement.requirement_id,
        chapter_id=requirement.chapter_id,
        chapter_name_ja=requirement.chapter_name_ja,
        chapter_name_en=requirement.chapter_name_en,
        section_id=requirement.section_id,
        section_name_ja=requirement.section_name_ja,
        section_name_en=requirement.section_name_en,
        description_ja=requirement.description_ja,
        description_en=requirement.description_en,
        level=requirement.level,
        translation_status="community-draft",
        official_english_source=_OFFICIAL_SOURCE,
        japanese_translation_source=_JAPANESE_SOURCE,
    )


def _search_key(value: str) -> str:
    key = value.lower().replace(".", "-")
    if not _SEARCH_KEY.fullmatch(key):
        raise ValueError(f"Generated chunk ID is not a valid Azure Search key: {key}")
    return key
