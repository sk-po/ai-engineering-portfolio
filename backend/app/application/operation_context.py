from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """現在の非同期処理コンテキストに設定された要求IDを取得する。

    Returns:
        HTTP要求の処理中に設定されたUUID形式のID。HTTP要求外で実行された場合はNone。
    """
    return _request_id.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """現在の非同期処理コンテキストへ要求IDを設定する。

    Args:
        request_id: middlewareが生成した、空でない要求相関ID。

    Returns:
        処理完了後に以前のコンテキストへ戻すためのToken。

    Raises:
        ValueError: request_idが空文字または空白だけの場合。
    """
    if not request_id.strip():
        raise ValueError("request_id must not be blank")
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """要求処理の終了後に要求IDのコンテキストを元へ戻す。

    Args:
        token: set_request_idが返した同一コンテキスト用のToken。

    Returns:
        None。
    """
    _request_id.reset(token)
