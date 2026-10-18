from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.application.operation_context import reset_request_id, set_request_id
from app.observability import get_logger

logger = get_logger(__name__)


def get_path_template(request: Request) -> str:
    """アクセスログ向けに値を含まないルートテンプレートを取得する。

    Args:
        request: FastAPIが受信したHTTP要求。

    Returns:
        解決済みルートのpathテンプレート。未解決のURLは入力値を記録せず`<unmatched>`。
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "<unmatched>"


async def observe_http_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """要求コンテキストを設定し、応答との相関情報とaccess logを付与する。

    Args:
        request: FastAPIが受信したHTTP要求。
        call_next: 次のmiddlewareまたはendpointを実行する非同期関数。

    Returns:
        endpointまたは例外handlerが生成し、`X-Request-ID`を付与したHTTPレスポンス。

    Notes:
        要求ごとにUUID形式のIDを生成し、総所要時間をaccess logへ記録する。
        処理完了時は、後続処理へ要求IDが漏れないようContextVarを元へ戻す。
    """
    request_id = uuid4().hex
    request.state.request_id = request_id
    token = set_request_id(request_id)
    started = perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request.completed",
            method=request.method,
            path_template=get_path_template(request),
            status_code=response.status_code,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return response
    finally:
        reset_request_id(token)


def register_middlewares(application: FastAPI) -> None:
    """FastAPIアプリへHTTP要求の観測用middlewareを登録する。

    Args:
        application: middlewareを登録するFastAPIアプリケーション。

    Returns:
        None。渡されたアプリケーションのmiddleware設定を変更する。

    Notes:
        同じアプリケーションへ複数回呼び出すと重複登録になるため、composition rootで
        1回だけ呼び出す。
    """
    application.middleware("http")(observe_http_request)
