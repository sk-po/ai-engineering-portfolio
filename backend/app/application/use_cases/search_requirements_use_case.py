from typing import Literal

from app.application.ports import RequirementRepository
from app.domain.models.asvs_requirement_model import RequirementMatch


class SearchRequirements:
    def __init__(self, repository: RequirementRepository) -> None:
        """検索処理を委譲するrepositoryを保持する。

        Args:
            repository: CSVやAzureなど、要件検索のportを実装したオブジェクト。
        """
        self._repository = repository

    async def execute(
        self,
        query: str,
        *,
        level: int | None = 2,
        limit: int = 5,
        level_filter: Literal["at_most", "exact"] = "at_most",
    ) -> tuple[RequirementMatch, ...]:
        """検索条件を検証し、repositoryへ要件検索を委譲する。

        Args:
            query: 検索文。前後の空白を除去して使用する。
            level: 対象Level。level_filterがat_mostなら上限、exactなら完全一致。
                既定は2、Noneはat_mostで全Levelを対象とする。
            limit: 最大取得件数（1〜10）。既定は5。
            level_filter: Levelの絞り込み方法。at_mostは指定値以下、exactは指定値だけを対象とする。

        Returns:
            repositoryが返した検索結果のタプル。該当なしは空タプル。

        Raises:
            ValueError: 検索文が空、またはLevel・件数が許容範囲外の場合。
            RequirementSearchUnavailableError: Azure検索などの委譲先が利用不能な場合。
        """
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        if level not in {None, 1, 2, 3}:
            raise ValueError("level must be 1, 2, 3, or None")
        if level_filter not in {"at_most", "exact"}:
            raise ValueError("level_filter must be at_most or exact")
        if level_filter == "exact" and level is None:
            raise ValueError("exact level_filter requires a level")
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")
        return await self._repository.search(
            normalized_query,
            level=level,
            limit=limit,
            level_filter=level_filter,
        )

    async def execute_per_level(
        self, query: str, *, target_level: int, limit_per_level: int = 5
    ) -> tuple[RequirementMatch, ...]:
        """選択LevelまでをLevelごとに独立して検索し、結果をLevel順に結合する。

        Args:
            query: 検索文。前後の空白を除去して各検索に使用する。
            target_level: 検索する最上位Level。1〜3だけを受け付ける。
            limit_per_level: 各Levelから返す最大件数。1〜10で、既定は5。

        Returns:
            L1からtarget_levelまで、各Levelの関連度順で連結した検索結果。

        Raises:
            ValueError: 検索文、Level、件数が許容範囲外の場合。
            RequirementSearchUnavailableError: 委譲先の検索が利用不能な場合。
        """
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        if target_level not in {1, 2, 3}:
            raise ValueError("target_level must be 1, 2, or 3")
        if not 1 <= limit_per_level <= 10:
            raise ValueError("limit_per_level must be between 1 and 10")

        matches: list[RequirementMatch] = []
        for current_level in range(1, target_level + 1):
            matches.extend(
                await self._repository.search(
                    normalized_query,
                    level=current_level,
                    limit=limit_per_level,
                    level_filter="exact",
                )
            )
        return tuple(matches)
