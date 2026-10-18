import unittest
from typing import Literal

from app.application.use_cases import SearchRequirements
from app.domain.models import AsvsRequirement, RequirementMatch


class FakeRequirementRepository:
    def __init__(self) -> None:
        self.arguments: list[
            tuple[str, int | None, int, Literal["at_most", "exact"]]
        ] = []
        requirement = AsvsRequirement(
            requirement_id="V6.1.1",
            chapter_id="V6",
            chapter_name_ja="認証",
            chapter_name_en="Authentication",
            section_id="V6.1",
            section_name_ja="認証セキュリティ",
            section_name_en="Authentication Security",
            description_ja="認証要件",
            description_en="Authentication requirement",
            level=1,
        )
        self.result = (RequirementMatch(requirement, 0.8),)

    async def search(
        self,
        query: str,
        *,
        level: int | None,
        limit: int,
        level_filter: Literal["at_most", "exact"] = "at_most",
    ) -> tuple[RequirementMatch, ...]:
        self.arguments.append((query, level, limit, level_filter))
        return self.result


class SearchRequirementsTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = FakeRequirementRepository()
        self.use_case = SearchRequirements(self.repository)

    async def test_searches_with_normalized_query_and_filters(self) -> None:
        result = await self.use_case.execute("  認証要件  ", level=1, limit=3)

        self.assertEqual(result, self.repository.result)
        self.assertEqual(self.repository.arguments, [("認証要件", 1, 3, "at_most")])

    async def test_searches_each_level_with_its_own_limit(self) -> None:
        result = await self.use_case.execute_per_level("認証要件", target_level=3)

        self.assertEqual(result, self.repository.result * 3)
        self.assertEqual(
            self.repository.arguments,
            [
                ("認証要件", 1, 5, "exact"),
                ("認証要件", 2, 5, "exact"),
                ("認証要件", 3, 5, "exact"),
            ],
        )

    async def test_rejects_blank_query(self) -> None:
        with self.assertRaises(ValueError):
            await self.use_case.execute("   ")

    async def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            await self.use_case.execute("認証", limit=11)


if __name__ == "__main__":
    unittest.main()
