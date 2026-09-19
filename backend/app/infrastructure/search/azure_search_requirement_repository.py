from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from app.application.ports.asvs_indexing import EmbeddingClient
from app.domain.models import RequirementMatch

VECTOR_DIMENSIONS = 1536
VECTOR_FIELD = "content_vector"
SELECT_FIELDS = (
    "requirement_id",
    "chapter_id",
    "chapter_name_ja",
    "chapter_name_en",
    "section_id",
    "section_name_ja",
    "section_name_en",
    "description_ja",
    "description_en",
    "level",
    "version",
)


class VectorSearchClient(Protocol):
    def search(
        self, search_text: str | None = None, **kwargs: Any
    ) -> Iterable[Mapping[str, Any]]: ...


class AzureSearchRequirementRepository:
    """Learning skeleton for the runtime vector-search adapter.

    Implement the TODOs before connecting this class to FastAPI dependency
    injection. Detailed implementation notes remain outside the public design.
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        search_client: VectorSearchClient,
    ) -> None:
        self._embedding_client = embedding_client
        self._search_client = search_client

    def search(
        self, query: str, *, level: int | None, limit: int
    ) -> tuple[RequirementMatch, ...]:
        # TODO(VEC-01, VEC-05, VEC-06): create and validate the query vector.
        # TODO(VEC-02..04): build VectorizedQuery, filter, select, and top.
        # TODO(VEC-07..09): convert every Azure result to RequirementMatch.
        raise NotImplementedError(
            "Implement the vector retrieval exercise described in the design document"
        )

    def _embed_query(self, query: str) -> tuple[float, ...]:
        raise NotImplementedError

    @staticmethod
    def _build_filter(level: int | None) -> str:
        raise NotImplementedError

    @staticmethod
    def _to_requirement_match(result: Mapping[str, Any]) -> RequirementMatch:
        raise NotImplementedError
