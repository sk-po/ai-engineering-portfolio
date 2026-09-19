from typing import Protocol

from app.domain.models.asvs_requirement import RequirementMatch


class RequirementRepository(Protocol):
    def search(
        self, query: str, *, level: int | None, limit: int
    ) -> tuple[RequirementMatch, ...]: ...
