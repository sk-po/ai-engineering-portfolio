import logging

import structlog
from structlog.stdlib import BoundLogger
from structlog.typing import EventDict, WrappedLogger

from app.application.operation_context import get_request_id

_configured = False
_missing = object()


def _add_log_level(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """業務項目のlevelを保持しながらログレベルをlog_levelへ追加する。

    Args:
        logger: structlogが渡す基底logger。
        method_name: infoやerrorなどのログメソッド名。
        event_dict: 呼び出し元が構築したログ項目。

    Returns:
        log_levelを追加し、既存のlevelがあれば元の値を保持したログ項目。
    """
    business_level = event_dict.pop("level", _missing)
    structlog.stdlib.add_log_level(logger, method_name, event_dict)
    event_dict["log_level"] = event_dict.pop("level")
    if business_level is not _missing:
        event_dict["level"] = business_level
    return event_dict


def _add_request_id(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """現在の要求IDを、存在する場合だけログイベントへ追加する。

    Args:
        logger: structlogが渡す基底logger。本processorでは参照しない。
        method_name: infoやerrorなどのログメソッド名。本processorでは参照しない。
        event_dict: これまでのprocessorと呼び出し元が構築したログ項目。

    Returns:
        HTTP要求の処理中ならrequest_idを追加したログ項目。要求外なら入力と同内容。
    """
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    """アプリケーション用structlogをJSON形式で一度だけ設定する。

    Returns:
        None。`app` loggerへハンドラーがなければ標準エラー用ハンドラーを追加する。

    Notes:
        timestamp、level、logger、request_idを共通processorで付与する。
        Uvicorn自身のログ設定は変更せず、`app`配下のloggerだけを対象とする。
    """

    # ログの構成はプロセス内で一度のみ実行
    global _configured
    if _configured:
        return

    # Structlogの加工処理を定義
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            _add_log_level,  # 関数を読んで、ログ出力項目に追加
            _add_request_id,  # 関数を読んで、ログ出力項目に追加
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # python標準ロガーへの設定

    # アプリケーション全体の親Logger。親子判定は、logger名を.で区切った文字列によって親子を判定
    # 子のロガーは[logger = get_logger(__name__)]で取得されることにより、nameのappが入るので親子を表現できる。
    # 　ex) app/infrastructure/external/example.py ⇒ nameはapp.infrastructure.external.example
    application_logger = logging.getLogger("app")
    application_logger.setLevel(logging.DEBUG)  # 出力ログレベルの設定
    if not application_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        application_logger.addHandler(handler)
    application_logger.propagate = False
    _configured = True


def get_logger(name: str) -> BoundLogger:
    """設定済みのstructlog loggerを取得する。

    Args:
        name: Pythonモジュール名など、ログ生成元を識別するlogger名。

    Returns:
        標準loggingへJSONログを渡すstructlogのbound logger。
    """
    configure_logging()
    return structlog.stdlib.get_logger(name)
