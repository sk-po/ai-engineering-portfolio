from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases import GenerateRequirementAnswer, SearchRequirements
from app.presentation.api.api_dependencies import (
    get_generate_requirement_answer,
    get_search_requirements,
)
from app.presentation.api.schemas.asvs_schema import (
    RequirementAnswerRequest,
    RequirementAnswerResponse,
    RequirementResponse,
    RequirementSearchRequest,
    RequirementSearchResponse,
)

router = APIRouter(prefix="/api/v1/requirements", tags=["ASVS requirements"])
SearchUseCase = Annotated[SearchRequirements, Depends(get_search_requirements)]
AnswerUseCase = Annotated[
    GenerateRequirementAnswer, Depends(get_generate_requirement_answer)
]


@router.post("/search", response_model=RequirementSearchResponse)
async def search_requirements(
    request: RequirementSearchRequest,
    use_case: SearchUseCase,
) -> RequirementSearchResponse:
    """検索条件をユースケースへ渡し、ASVS要件をHTTPレスポンス形式で返す。

    Args:
        request: 入力検証済みの検索文・Level上限・取得件数。
        use_case: FastAPIのDependsから注入される検索ユースケース。

    Returns:
        検索条件、要件一覧、翻訳の注意書きと出典を含むレスポンス。

    Raises:
        RequirementSearchUnavailableError: 検索に失敗した場合。
            アプリの例外ハンドラーがHTTP 503へ変換する。

    Notes:
        Azure検索は非同期SDKをawaitして実行する。CSV検索はrepository内で
        worker threadへ退避するため、いずれの検索方式もイベントループをブロックしない。
    """
    matches = await use_case.execute(
        request.query,
        level=request.level,
        limit=request.limit,
    )
    return RequirementSearchResponse(
        query=request.query,
        level=request.level,
        results=[RequirementResponse.from_domain(match) for match in matches],
    )


@router.post("/answer", response_model=RequirementAnswerResponse)
async def generate_requirement_answer(
    request: RequirementAnswerRequest,
    use_case: AnswerUseCase,
) -> RequirementAnswerResponse:
    """質問に関連するASVS要件を検索し、根拠付きの生成回答を返す。

    Args:
        request: 入力検証済みの質問・Level上限・根拠の最大取得件数。
        use_case: FastAPIのDependsから注入される検索・生成ユースケース。

    Returns:
        生成回答と、生成モデルへ渡したASVS検索結果を含むレスポンス。

    Raises:
        RequirementSearchUnavailableError: 根拠検索に失敗した場合。
        RequirementAnswerUnavailableError: OpenAI APIでの生成に失敗した場合。

    Notes:
        利用者の質問と検索された要件本文はOpenAI APIへ送信される。
    """
    result = await use_case.execute(
        request.query,
        level=request.level,
        limit=request.limit,
    )
    return RequirementAnswerResponse.from_application(
        query=request.query,
        level=request.level,
        result=result,
    )
