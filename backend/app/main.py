from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.presentation.api.routers import asvs_router, greeting_router, health_router


def create_app() -> FastAPI:
    """ルーターと検索障害用ハンドラーを登録したFastAPIアプリを生成する。

    Returns:
        ASVS検索、挨拶、ヘルスチェックのルーターを持つアプリ。
        この関数ではサーバーの起動やAzure検索は行わない。
    """
    application = FastAPI(
        title="ASVS Requirement Search API",
        description="Search OWASP ASVS 5.0.0 in Japanese and English.",
        version="0.2.0",
    )
    application.include_router(asvs_router.router)
    application.include_router(greeting_router.router)
    application.include_router(health_router.router)

    @application.exception_handler(RequirementSearchUnavailableError)
    async def search_unavailable(
        request: Request, error: RequirementSearchUnavailableError
    ) -> JSONResponse:
        """検索不能エラーを、内部情報を含まないHTTP 503へ変換する。

        Args:
            request: FastAPIから渡される対象リクエスト。本処理では参照しない。
            error: 捕捉した検索不能エラー。詳細はレスポンスに含めない。

        Returns:
            固定のdetailメッセージとステータス503を持つJSONレスポンス。
        """
        return JSONResponse(
            status_code=503,
            content={"detail": "Requirement search is temporarily unavailable"},
        )

    return application


app = create_app()
