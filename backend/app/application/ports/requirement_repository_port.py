from typing import Literal, Protocol

from app.domain.models.asvs_requirement_model import RequirementMatch


class RequirementRepository(Protocol):
    async def search(
        self,
        query: str,
        *,
        level: int | None,
        limit: int,
        level_filter: Literal["at_most", "exact"] = "at_most",
    ) -> tuple[RequirementMatch, ...]: ...
