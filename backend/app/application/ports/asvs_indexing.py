from collections.abc import Sequence
from typing import Protocol

from app.application.models import EmbeddedAsvsIndexDocument
from app.domain.models import AsvsRequirement


class AsvsRequirementSource(Protocol):
    def list_all(self) -> tuple[AsvsRequirement, ...]: ...


class EmbeddingClient(Protocol):
    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


class SearchDocumentWriter(Protocol):
    def merge_or_upload(
        self, documents: Sequence[EmbeddedAsvsIndexDocument]
    ) -> int: ...
