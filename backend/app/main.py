from fastapi import FastAPI

from app.presentation.api.exception_handlers import register_exception_handlers
from app.presentation.api.middleware import register_middlewares
from app.presentation.api.routers import (
    asvs_router,
    asvs_v2_router,
    greeting_router,
    guided_requirements_v2_router,
    health_router,
)


def create_app() -> FastAPI:
    """ルーター、middleware、例外handlerを登録したFastAPIアプリを生成する。

    Returns:
        ASVS検索、挨拶、ヘルスチェックのルーターを持つアプリ。
        この関数ではサーバーの起動やAzure検索は行わない。

    Notes:
        app配下のログはstructlogの共通設定によりINFO以上のJSONとして出力する。
    """
    application = FastAPI(
        title="ASVS Requirement Search API",
        description="Search OWASP ASVS 5.0.0 in Japanese and English.",
        version="0.2.0",
    )
    application.include_router(asvs_router.router)
    application.include_router(asvs_v2_router.router)
    application.include_router(guided_requirements_v2_router.router)
    application.include_router(greeting_router.router)
    application.include_router(health_router.router)
    register_middlewares(application)
    register_exception_handlers(application)

    return application


app = create_app()
