from typing import Annotated, Literal

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_search_backend(value: object) -> object:
    """検索方式の文字列を空白除去・小文字化して検証へ渡す。

    Args:
        value: 環境変数または初期化引数から受け取った値。

    Returns:
        文字列なら前後の空白を除いて小文字化した値。それ以外は元の値。
    """
    if isinstance(value, str):
        return value.strip().lower()
    return value


SearchBackend = Annotated[
    Literal["csv", "azure"], BeforeValidator(_normalize_search_backend)
]


class RuntimeSettings(BaseSettings):
    """バックエンド全体の動作方式をコンテナ環境変数から読み込む。"""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=None,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )

    search_backend: SearchBackend = Field(
        default="csv", validation_alias="ASVS_SEARCH_BACKEND"
    )
