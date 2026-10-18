from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveFloat = Annotated[float, Field(gt=0)]
PositiveInteger = Annotated[int, Field(gt=0)]


class AnswerSettings(BaseSettings):
    """OpenAI回答生成の認証・モデル・上限設定を環境変数から読み込む。"""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=None,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )

    api_key: SecretStr = Field(
        min_length=1,
        validation_alias="OPENAI_API_KEY",
    )
    chat_model: NonEmptyString = Field(validation_alias="OPENAI_CHAT_MODEL")
    timeout_seconds: PositiveFloat = Field(
        default=30.0,
        validation_alias="OPENAI_CHAT_TIMEOUT_SECONDS",
    )
    max_completion_tokens: PositiveInteger = Field(
        default=800,
        validation_alias="OPENAI_CHAT_MAX_COMPLETION_TOKENS",
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def strip_api_key(cls, value: object) -> object:
        """APIキー文字列の前後の空白を除去して空値検証へ渡す。

        Args:
            value: 環境変数または初期化引数から受け取ったAPIキー。

        Returns:
            文字列なら前後の空白を除いた値。それ以外は元の値。
        """
        if isinstance(value, str):
            return value.strip()
        return value
