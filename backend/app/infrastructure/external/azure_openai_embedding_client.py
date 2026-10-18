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
        timeout_seconds: float | None = None,
        sdk_client: Any | None = None,
        rate_limit_error_type: type[Exception] | None = None,
    ) -> None:
        """Embedding APIの接続と、レート制限時の再試行を設定する。

        Args:
            base_url: /openai/v1/で終わるAzure OpenAIの接続先URL。
            deployment_name: 登録・検索で共通して使うEmbeddingのDeployment名。
            credential: SDK生成時にトークンを取得するEntra ID認証オブジェクト。
            dimensions: 生成するベクトルの次元数。既定は1536。
            max_rate_limit_retries: レート制限時の最大再試行回数。0なら再試行しない。
            rate_limit_wait_seconds: 応答から待機時間を取得できない場合の秒数。
            rate_limit_buffer_seconds: 待機時間に加える余裕時間（秒）。
            on_rate_limit: 再試行番号と待機秒数を受け取る通知関数。Noneなら通知しない。
            sleep: 待機に使用する関数。テスト時は待機しない関数を注入できる。
            timeout_seconds: SDK生成時に指定するtimeout（秒）。NoneはSDK既定値。
            sdk_client: テストなどで注入するSDK。Noneなら認証付きSDKを生成する。
            rate_limit_error_type: 注入SDKのレート制限例外型。通常はSDKの型を使う。

        Raises:
            ValueError: 接続設定が空、次元数や待機・再試行設定が不正な場合。

        Notes:
            この時点ではEmbedding APIを呼ばない。SDKを注入した場合、
            認証・URL正規化・SDKのtimeout設定はこのクラスでは行わない。
        """
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
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

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
            if timeout_seconds is None:
                sdk_client = OpenAI(
                    base_url=_normalize_base_url(base_url),
                    api_key=token_provider,
                    # Retry is handled below so nested retries don't create another
                    # burst inside Azure's rate-limit window.
                    max_retries=0,
                )
            else:
                sdk_client = OpenAI(
                    base_url=_normalize_base_url(base_url),
                    api_key=token_provider,
                    max_retries=0,
                    timeout=timeout_seconds,
                )
            rate_limit_error_type = RateLimitError
        elif rate_limit_error_type is None:
            from openai import RateLimitError

            rate_limit_error_type = RateLimitError
        self._client = sdk_client
        self._rate_limit_error_type = rate_limit_error_type

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """文章をEmbedding APIでベクトル化し、入力順で返す。

        Args:
            texts: ベクトル化する文章の列。空なら外部通信を行わない。

        Returns:
            各文章に対応する浮動小数点数のベクトルのタプル。空入力は空タプル。

        Notes:
            SDKの認証・通信エラーは呼び出し元へ伝える。
            返却件数や次元数の検証は、このクライアントの利用側が行う。
        """
        if not texts:
            return ()
        response = self._create_with_rate_limit_retry(texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return tuple(
            tuple(float(value) for value in item.embedding) for item in ordered
        )

    def _create_with_rate_limit_retry(self, texts: Sequence[str]) -> Any:
        """Embedding APIを呼び、レート制限時だけ待機して再試行する。

        Args:
            texts: 1回のAPI要求で送信する文章の列。

        Returns:
            ベクトルと入力位置などを含むSDKの応答オブジェクト。

        Notes:
            上限まで再試行しても成功しない場合はレート制限例外を再送出する。
            その他の例外は再試行せず伝える。待機時間は応答ヘッダーを優先し、
            設定された余裕時間を加える。通知関数があれば待機前に呼び出す。
        """
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
                wait_seconds = (
                    _retry_after_seconds(error, fallback=self._rate_limit_wait_seconds)
                    + self._rate_limit_buffer_seconds
                )
                if self._on_rate_limit is not None:
                    self._on_rate_limit(retry_count, wait_seconds)
                self._sleep(wait_seconds)


class AsyncAzureOpenAIEmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str,
        deployment_name: str,
        credential: Any,
        dimensions: int = 1536,
        timeout_seconds: float | None = None,
        sdk_client: Any | None = None,
    ) -> None:
        """Runtime検索用の非同期Embeddingクライアントを設定する。

        Args:
            base_url: /openai/v1/で終わるAzure OpenAIの接続先URL。
            deployment_name: 検索時に使うEmbeddingのDeployment名。
            credential: SDK生成時にEntra IDトークンを取得する認証オブジェクト。
            dimensions: 生成するベクトルの次元数。既定は1536。
            timeout_seconds: SDKの各要求timeout（秒）。NoneならSDK既定値を使う。
            sdk_client: テスト用に注入する非同期SDK。NoneならSDKを生成する。

        Raises:
            ValueError: 接続設定、次元数、またはtimeoutが不正な場合。

        Notes:
            この時点では外部通信を行わない。runtime検索では再試行を無効にするため、
            レート制限の待機・再試行機能は持たせない。
        """
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not deployment_name.strip():
            raise ValueError("deployment_name is required")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._deployment_name = deployment_name
        self._dimensions = dimensions
        if sdk_client is None:
            from azure.identity.aio import get_bearer_token_provider
            from openai import AsyncOpenAI

            token_provider = get_bearer_token_provider(credential, _TOKEN_SCOPE)
            if timeout_seconds is None:
                sdk_client = AsyncOpenAI(
                    base_url=_normalize_base_url(base_url),
                    api_key=token_provider,
                    max_retries=0,
                )
            else:
                sdk_client = AsyncOpenAI(
                    base_url=_normalize_base_url(base_url),
                    api_key=token_provider,
                    max_retries=0,
                    timeout=timeout_seconds,
                )
        self._client = sdk_client

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """文章を非同期Embedding APIでベクトル化し、入力順で返す。

        Args:
            texts: ベクトル化する文章の列。空なら外部通信を行わない。

        Returns:
            各文章に対応する浮動小数点数のベクトルのタプル。空入力は空タプル。

        Notes:
            SDKの認証・通信エラーは呼び出し元へ伝える。返却件数や次元数の検証は
            利用側で行う。
        """
        if not texts:
            return ()
        response = await self._client.embeddings.create(
            model=self._deployment_name,
            input=list(texts),
            dimensions=self._dimensions,
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return tuple(
            tuple(float(value) for value in item.embedding) for item in ordered
        )

    async def close(self) -> None:
        """SDKが保持する非同期HTTP接続を閉じる。

        Returns:
            None。
        """
        await self._client.close()


def _normalize_base_url(value: str) -> str:
    """接続先URLの表記を整え、OpenAI v1のパスを検証する。

    Args:
        value: 設定された接続先URL。

    Returns:
        前後の空白を除去し、末尾のスラッシュを1つにしたURL。

    Raises:
        ValueError: 正規化後の末尾が/openai/v1/でない場合。
    """
    base_url = value.strip().rstrip("/") + "/"
    if not base_url.endswith("/openai/v1/"):
        raise ValueError("base_url must end with /openai/v1/")
    return base_url


def _retry_after_seconds(error: Exception, *, fallback: float) -> float:
    """レート制限応答のヘッダーから再試行前の待機秒数を求める。

    Args:
        error: response.headersを持つSDK例外。持たない例外も受け付ける。
        fallback: 有効な待機時間が取得できない場合に返す秒数。

    Returns:
        retry-after-ms、数値のretry-after、fallbackの優先順で得た秒数。
        ヘッダーの負の値は0に補正する。HTTP日時形式は解釈せずfallbackを使う。
    """
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
