from app.application.ports import RequirementRepository
from app.domain.models.asvs_requirement import RequirementMatch


class SearchRequirements:
    def __init__(self, repository: RequirementRepository) -> None:
        self._repository = repository

    def execute(
        self, query: str, *, level: int | None = 2, limit: int = 5
    ) -> tuple[RequirementMatch, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        if level not in {None, 1, 2, 3}:
            raise ValueError("level must be 1, 2, 3, or None")
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")
        return self._repository.search(
            normalized_query, level=level, limit=limit
        )
