from functools import lru_cache
from pathlib import Path

from app.application.use_cases import CreateGreeting
from app.application.use_cases import SearchRequirements
from app.infrastructure.repositories import CsvAsvsRequirementRepository


def get_create_greeting() -> CreateGreeting:
    return CreateGreeting()


@lru_cache #これは、Pythonの関数の戻り値をキャッシュしている。結果、Singleton相当の実装になっている。このキャッシュはPythonのプロセス単位
def get_search_requirements() -> SearchRequirements:
    data_directory = (
        Path(__file__).resolve().parents[2] / "infrastructure" / "data"
    )
    repository = CsvAsvsRequirementRepository(
        data_directory / "asvs-5.0.0-en.csv",
        data_directory / "asvs-5.0.0-ja.csv",
    )
    return SearchRequirements(repository)
