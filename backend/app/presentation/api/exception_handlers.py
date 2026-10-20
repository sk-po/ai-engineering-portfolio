from traceback import extract_tb

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.application_errors import ApplicationError
from app.application.operation_context import (
    get_request_id,
    reset_request_id,
    set_request_id,
)
from app.application.requirement_answer_errors import RequirementAnswerUnavailableError
from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.observability import get_logger
from app.presentation.api.middleware import get_path_template

logger = get_logger(__name__)

_APPLICATION_ERROR_RESPONSES: tuple[tuple[type[ApplicationError], int, str], ...] = (
    (
        RequirementSearchUnavailableError,
        503,
        "Requirement search is temporarily unavailable",
    ),
    (
        RequirementAnswerUnavailableError,
        503,
        "Requirement answer generation is temporarily unavailable",
    ),
)


def _get_application_error_response(
    error: ApplicationError,
) -> tuple[int, str] | None:
    """application例外に対応する公開HTTPレスポンス定義を取得する。

    Args:
        error: application層から送出された共通基底クラスの派生例外。

    Returns:
        対応するHTTPステータスと安全なdetailの組。未登録の派生例外ならNone。
    """
    for error_type, status_code, detail in _APPLICATION_ERROR_RESPONSES:
        if isinstance(error, error_type):
            return status_code, detail
    return None


async def handle_application_error(
    request: Request, error: ApplicationError
) -> JSONResponse:
    """既知のapplication例外を内部情報を含まないHTTPエラーへ変換する。

    Args:
        request: FastAPIが受信したHTTP要求。相関IDの取得に使用する。
        error: application層から送出された共通基底クラスの派生例外。

    Returns:
        登録済みの例外なら対応するHTTPレスポンス。未登録なら安全な500レスポンス。
    """
    response_definition = _get_application_error_response(error)
    if response_definition is None:
        return await handle_unexpected_error(request, error)

    status_code, detail = response_definition
    logger.error(
        "http_exception.handled",
        status_code=status_code,
        error_type=type(error).__name__,
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


async def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """入力検証エラーを本文を記録せずに観測し、標準422応答を返す。

    Args:
        request: 入力検証に失敗したHTTP要求。
        error: FastAPIが生成した検証エラー。入力本文は参照しない。

    Returns:
        FastAPI標準の422レスポンス。相関IDヘッダーはmiddlewareが付与する。
    """
    logger.info(
        "http_request.validation_failed",
        path_template=get_path_template(request),
        status_code=422,
        error_count=len(error.errors()),
    )
    return await request_validation_exception_handler(request, error)


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    """未分類例外を安全な500へ変換し、秘密情報を含まない診断情報を記録する。

    Args:
        request: 未分類例外が発生したHTTP要求。
        error: 想定外の例外。例外本文はログ・レスポンスへ出力しない。

    Returns:
        固定detailと相関IDヘッダーを持つHTTP 500レスポンス。
    """
    request_id = getattr(request.state, "request_id", None)
    token = (
        set_request_id(request_id)
        if isinstance(request_id, str) and request_id and not get_request_id()
        else None
    )
    try:
        logger.error(
            "http_exception.unexpected",
            status_code=500,
            error_type=type(error).__name__,
            stack_frames=[
                {
                    "filename": frame.filename,
                    "line": frame.lineno,
                    "function": frame.name,
                }
                for frame in extract_tb(error.__traceback__)
            ],
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={"X-Request-ID": request_id or ""},
        )
    finally:
        if token is not None:
            reset_request_id(token)


def register_exception_handlers(application: FastAPI) -> None:
    """FastAPIアプリへapplication・検証・未分類例外のhandlerを登録する。

    Args:
        application: 例外handlerを登録するFastAPIアプリケーション。

    Returns:
        None。渡されたアプリケーションの例外handler設定を変更する。

    Notes:
        application例外は共通基底のApplicationErrorへ一度だけ登録し、派生例外も
        FastAPIの例外クラス探索で同じhandlerへ集約する。
    """

    # 例外の基本方針としては、アプリ例外、バリデーション(FastAPI)、予期せぬエラーの３つを構成する
    application.exception_handler(ApplicationError)(handle_application_error)
    application.exception_handler(RequestValidationError)(handle_validation_error)
    application.exception_handler(Exception)(handle_unexpected_error)
