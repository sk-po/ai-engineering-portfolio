import time
from collections.abc import Callable, Sequence
from typing import Any

_TOKEN_SCOPE = "https://ai.azure.com/.default"


class AzureOpenAIEmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str,
        deployment_name: str,
        credential: Any,
        dimensions: int = 1536,
        max_rate_limit_retries: int = 10,
        rate_limit_wait_seconds: float = 60.0,
        rate_limit_buffer_seconds: float = 5.0,
        on_rate_limit: Callable[[int, float], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        sdk_client: Any | None = None,
        rate_limit_error_type: type[Exception] | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not deployment_name.strip():
            raise ValueError("deployment_name is required")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        if max_rate_limit_retries < 0:
            raise ValueError("max_rate_limit_retries must not be negative")
        if rate_limit_wait_seconds < 0:
            raise ValueError("rate_limit_wait_seconds must not be negative")
        if rate_limit_buffer_seconds < 0:
            raise ValueError("rate_limit_buffer_seconds must not be negative")

        self._deployment_name = deployment_name
        self._dimensions = dimensions
        self._max_rate_limit_retries = max_rate_limit_retries
        self._rate_limit_wait_seconds = rate_limit_wait_seconds
        self._rate_limit_buffer_seconds = rate_limit_buffer_seconds
        self._on_rate_limit = on_rate_limit
        self._sleep = sleep
        if sdk_client is None:
            from azure.identity import get_bearer_token_provider
            from openai import OpenAI, RateLimitError

            token_provider = get_bearer_token_provider(credential, _TOKEN_SCOPE)
            sdk_client = OpenAI(
                base_url=_normalize_base_url(base_url),
                api_key=token_provider,
                # Retry is handled below so nested retries don't create another
                # burst inside Azure's rate-limit window.
                max_retries=0,
            )
            rate_limit_error_type = RateLimitError
        elif rate_limit_error_type is None:
            from openai import RateLimitError

            rate_limit_error_type = RateLimitError
        self._client = sdk_client
        self._rate_limit_error_type = rate_limit_error_type

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        response = self._create_with_rate_limit_retry(texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return tuple(tuple(float(value) for value in item.embedding) for item in ordered)

    def _create_with_rate_limit_retry(self, texts: Sequence[str]) -> Any:
        retry_count = 0
        while True:
            try:
                return self._client.embeddings.create(
                    model=self._deployment_name,
                    input=list(texts),
                    dimensions=self._dimensions,
                    encoding_format="float",
                )
            except self._rate_limit_error_type as error:
                if retry_count >= self._max_rate_limit_retries:
                    raise
                retry_count += 1
                wait_seconds = _retry_after_seconds(
                    error, fallback=self._rate_limit_wait_seconds
                ) + self._rate_limit_buffer_seconds
                if self._on_rate_limit is not None:
                    self._on_rate_limit(retry_count, wait_seconds)
                self._sleep(wait_seconds)


def _normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/") + "/"
    if not base_url.endswith("/openai/v1/"):
        raise ValueError("base_url must end with /openai/v1/")
    return base_url


def _retry_after_seconds(error: Exception, *, fallback: float) -> float:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {})
    retry_after_ms = headers.get("retry-after-ms")
    if retry_after_ms is not None:
        try:
            return max(float(retry_after_ms) / 1000, 0)
        except (TypeError, ValueError):
            pass
    retry_after = headers.get("retry-after")
    if retry_after is not None:
        try:
            return max(float(retry_after), 0)
        except (TypeError, ValueError):
            pass
    return fallback
