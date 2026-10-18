from typing import Annotated

from pydantic import AnyHttpUrl, Field, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AzureSearchSettings(BaseSettings):
    """Azure AI SearchとEmbedding接続の設定を環境変数から読み込む。"""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=None,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )

    search_endpoint: AnyHttpUrl = Field(validation_alias="AZURE_SEARCH_ENDPOINT")
    search_index_name: NonEmptyString = Field(
        default="security-docs-v1", validation_alias="AZURE_SEARCH_INDEX_NAME"
    )
    openai_base_url: AnyHttpUrl = Field(validation_alias="AZURE_OPENAI_BASE_URL")
    embedding_deployment: NonEmptyString = Field(
        default="text-embedding-3-small",
        validation_alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    )
