from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases import SearchRequirements
from app.presentation.api.dependencies import get_search_requirements
from app.presentation.api.schemas.asvs import (
    RequirementResponse,
    RequirementSearchRequest,
    RequirementSearchResponse,
)

router = APIRouter(prefix="/api/v1/requirements", tags=["ASVS requirements"])
SearchUseCase = Annotated[SearchRequirements, Depends(get_search_requirements)]


@router.post("/search", response_model=RequirementSearchResponse)
async def search_requirements(
    request: RequirementSearchRequest,
    use_case: SearchUseCase,
) -> RequirementSearchResponse:
    matches = use_case.execute(
        request.query,
        level=request.level,
        limit=request.limit,
    )
    return RequirementSearchResponse(
        query=request.query,
        level=request.level,
        results=[RequirementResponse.from_domain(match) for match in matches],
    )
