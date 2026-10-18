from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases import GuideRequirements
from app.presentation.api.api_dependencies import get_guide_requirements
from app.presentation.api.schemas.guided_requirements_v2_schema import (
    GuidedRequirementsTurnRequest,
    GuidedRequirementsTurnResponse,
)

router = APIRouter(prefix="/api/v2/guided-requirements", tags=["guided requirements v2"])
GuideUseCase = Annotated[GuideRequirements, Depends(get_guide_requirements)]


@router.post("/turn", response_model=GuidedRequirementsTurnResponse)
async def guide_requirements_turn(
    request: GuidedRequirementsTurnRequest,
    use_case: GuideUseCase,
) -> GuidedRequirementsTurnResponse:
    """要件ヒアリングを1ターン進め、質問または根拠付き最終回答を返す。

    Args:
        request: 機能説明、これまでの回答、ASVS最上位Level。
        use_case: FastAPI依存性注入で得たヒアリングユースケース。

    Returns:
        次の質問、またはLevel別RAG根拠を含む最終回答。
    """
    result = await use_case.execute(
        request.feature_description, answers=request.answers, level=request.level
    )
    return GuidedRequirementsTurnResponse.from_application(
        result=result, level=request.level
    )
