from functools import lru_cache
from pathlib import Path

from app.application.requirement_answer_errors import RequirementAnswerUnavailableError
from app.application.requirement_search_errors import RequirementSearchUnavailableError
from app.application.use_cases import (
    CreateGreeting,
    GenerateRequirementAnswer,
    GuideRequirements,
    SearchRequirements,
)
from app.infrastructure.files import CsvAsvsRequirementRepository
from app.settings import AnswerSettings, AzureSearchSettings, RuntimeSettings


def get_create_greeting() -> CreateGreeting:
    """挨拶エンドポイントで使用するユースケースを生成する。

    Returns:
        呼び出しごとに生成したCreateGreetingインスタンス。
    """
    return CreateGreeting()


@lru_cache  # これは、Pythonの関数の戻り値をキャッシュしている。結果、Singleton相当の実装になっている。このキャッシュはPythonのプロセス単位
def get_search_requirements() -> SearchRequirements:
    """環境変数に従って検索方式を選び、ユースケースを提供する。

    Returns:
        CSVまたはAzureのrepositoryを組み込んだSearchRequirements。

    Raises:
        RequirementSearchUnavailableError: 検索方式の指定やAzure接続設定が不正な場合。

    Notes:
        ASVS_SEARCH_BACKENDは既定csv。azure指定時にAzure接続を構成する。
        引数はなく、設定を環境変数から取得する。CSV方式ではローカルファイルを読む。
        戻り値はプロセス内でキャッシュされ、設定変更後は再起動が必要。
    """
    try:
        settings = RuntimeSettings()
    except ValueError as error:
        raise RequirementSearchUnavailableError(
            "Invalid runtime configuration"
        ) from error
    if settings.search_backend == "azure":
        return _create_azure_search_requirements()
    data_directory = Path(__file__).resolve().parents[2] / "infrastructure" / "data"
    repository = CsvAsvsRequirementRepository(
        data_directory / "asvs-5.0.0-en.csv",
        data_directory / "asvs-5.0.0-ja.csv",
    )
    return SearchRequirements(repository)


def _create_azure_search_requirements() -> SearchRequirements:
    """環境変数からAzureクライアントを生成し、検索ユースケースを組み立てる。

    Returns:
        AzureSearchRequirementRepositoryを組み込んだSearchRequirements。

    Raises:
        RequirementSearchUnavailableError: 必須設定の欠落や接続設定の検証失敗。

    Notes:
        接続先・Index名・Deployment名は環境変数から取得する。
        この関数では検索せず、実際の通信はユースケース実行時に行う。
        HTTP要求用に再試行を無効化し、各SDKのtimeoutを設定する。
    """
    from azure.identity.aio import DefaultAzureCredential
    from azure.search.documents.aio import SearchClient

    from app.infrastructure.external import (
        AsyncAzureOpenAIEmbeddingClient,
        AzureSearchRequirementRepository,
    )

    try:
        settings = AzureSearchSettings()
        credential = DefaultAzureCredential()
        embedding_client = AsyncAzureOpenAIEmbeddingClient(
            base_url=str(settings.openai_base_url),
            deployment_name=settings.embedding_deployment,
            credential=credential,
            timeout_seconds=15.0,
        )
        search_client = SearchClient(
            endpoint=str(settings.search_endpoint).rstrip("/"),
            index_name=settings.search_index_name,
            credential=credential,
            retry_total=0,
            connection_timeout=5,
            read_timeout=15,
        )
    except ValueError as error:
        raise RequirementSearchUnavailableError(
            "Invalid Azure search configuration"
        ) from error
    return SearchRequirements(
        AzureSearchRequirementRepository(embedding_client, search_client)
    )


@lru_cache
def get_generate_requirement_answer() -> GenerateRequirementAnswer:
    """環境変数からOpenAI生成クライアントを作り、回答ユースケースを提供する。

    Returns:
        選択済み検索ユースケースとOpenAI生成clientを持つユースケース。

    Raises:
        RequirementAnswerUnavailableError: 必須設定の欠落または値が不正な場合。

    Notes:
        OPENAI_API_KEYとOPENAI_CHAT_MODELは必須。
        戻り値はプロセス内でキャッシュされ、設定変更後は再起動が必要。
    """
    from app.infrastructure.external import OpenAIRequirementAnswerClient

    try:
        settings = AnswerSettings()
        generator = OpenAIRequirementAnswerClient(
            api_key=settings.api_key.get_secret_value(),
            model=settings.chat_model,
            timeout_seconds=settings.timeout_seconds,
            max_completion_tokens=settings.max_completion_tokens,
        )
    except ValueError as error:
        raise RequirementAnswerUnavailableError(
            "Invalid OpenAI answer generation configuration"
        ) from error
    return GenerateRequirementAnswer(get_search_requirements(), generator)


@lru_cache
def get_guide_requirements() -> GuideRequirements:
    """OpenAIの判断clientと既存RAG回答を組み合わせた要件ヒアリングを提供する。

    Returns:
        質問、Level別RAG検索、最終回答を順番に実行するユースケース。

    Raises:
        RequirementAnswerUnavailableError: OpenAI設定が不正な場合。
    """
    from app.infrastructure.external import OpenAIGuidedRequirementsPlannerClient

    try:
        settings = AnswerSettings()
        planner = OpenAIGuidedRequirementsPlannerClient(
            api_key=settings.api_key.get_secret_value(),
            model=settings.chat_model,
            timeout_seconds=settings.timeout_seconds,
        )
    except ValueError as error:
        raise RequirementAnswerUnavailableError(
            "Invalid OpenAI answer generation configuration"
        ) from error
    return GuideRequirements(planner, get_generate_requirement_answer())
