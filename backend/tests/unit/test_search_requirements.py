import unittest

from app.application.use_cases import SearchRequirements
from app.domain.models import AsvsRequirement, RequirementMatch


class FakeRequirementRepository:
    def __init__(self) -> None:
        self.arguments: tuple[str, int | None, int] | None = None
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

    def search(
        self, query: str, *, level: int | None, limit: int
    ) -> tuple[RequirementMatch, ...]:
        self.arguments = (query, level, limit)
        return self.result


class SearchRequirementsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRequirementRepository()
        self.use_case = SearchRequirements(self.repository)

    def test_searches_with_normalized_query_and_filters(self) -> None:
        result = self.use_case.execute("  認証要件  ", level=1, limit=3)

        self.assertEqual(result, self.repository.result)
        self.assertEqual(self.repository.arguments, ("認証要件", 1, 3))

    def test_rejects_blank_query(self) -> None:
        with self.assertRaises(ValueError):
            self.use_case.execute("   ")

    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            self.use_case.execute("認証", limit=11)


if __name__ == "__main__":
    unittest.main()
