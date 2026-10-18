from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases import GenerateRequirementAnswer, SearchRequirements
from app.presentation.api.api_dependencies import (
    get_generate_requirement_answer,
    get_search_requirements,
)
from app.presentation.api.schemas.asvs_schema import RequirementResponse
from app.presentation.api.schemas.asvs_v2_schema import (
    RETRIEVAL_LIMIT_PER_LEVEL,
    LevelScopedAnswerResponse,
    LevelScopedRequirementRequest,
    LevelScopedRetrieval,
    LevelScopedSearchResponse,
)

router = APIRouter(prefix="/api/v2/requirements", tags=["ASVS requirements v2"])
SearchUseCase = Annotated[SearchRequirements, Depends(get_search_requirements)]
AnswerUseCase = Annotated[
    GenerateRequirementAnswer, Depends(get_generate_requirement_answer)
]


@router.post("/search", response_model=LevelScopedSearchResponse)
async def search_requirements_per_level(
    request: LevelScopedRequirementRequest,
    use_case: SearchUseCase,
) -> LevelScopedSearchResponse:
    """選択LevelまでをLevelごとに検索し、各Level最大5件の要件を返す。

    Args:
        request: 入力検証済みの検索文と最上位Level。
        use_case: FastAPIのDependsから注入される検索ユースケース。

    Returns:
        Level別の抽出条件、要件一覧、翻訳の注意書きと出典を含むレスポンス。

    Raises:
        RequirementSearchUnavailableError: 検索に失敗した場合。
            アプリの例外ハンドラーがHTTP 503へ変換する。
    """
    matches = await use_case.execute_per_level(
        request.query,
        target_level=request.level,
        limit_per_level=RETRIEVAL_LIMIT_PER_LEVEL,
    )
    return LevelScopedSearchResponse(
        query=request.query,
        level=request.level,
        retrieval=LevelScopedRetrieval.from_target_level(request.level),
        results=[RequirementResponse.from_domain(match) for match in matches],
    )


@router.post("/answer", response_model=LevelScopedAnswerResponse)
async def generate_requirement_answer_per_level(
    request: LevelScopedRequirementRequest,
    use_case: AnswerUseCase,
) -> LevelScopedAnswerResponse:
    """Level別に抽出したASVS要件だけを根拠に、生成回答を返す。

    Args:
        request: 入力検証済みの質問と最上位Level。
        use_case: FastAPIのDependsから注入される検索・生成ユースケース。

    Returns:
        生成回答、Level別に抽出してモデルへ渡した根拠要件、抽出条件を含むレスポンス。

    Raises:
        RequirementSearchUnavailableError: 根拠検索に失敗した場合。
        RequirementAnswerUnavailableError: OpenAI APIでの生成に失敗した場合。
    """
    result = await use_case.execute_per_level(
        request.query,
        target_level=request.level,
        limit_per_level=RETRIEVAL_LIMIT_PER_LEVEL,
    )
    return LevelScopedAnswerResponse.from_application(
        query=request.query,
        level=request.level,
        result=result,
    )
