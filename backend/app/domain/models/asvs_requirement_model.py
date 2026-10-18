from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AsvsRequirement:
    requirement_id: str
    chapter_id: str
    chapter_name_ja: str
    chapter_name_en: str
    section_id: str
    section_name_ja: str
    section_name_en: str
    description_ja: str
    description_en: str
    level: int
    version: str = "5.0.0"

    def __post_init__(self) -> None:
        if not self.requirement_id.startswith("V"):
            raise ValueError("ASVS requirement IDs must start with V")
        if self.level not in {1, 2, 3}:
            raise ValueError("ASVS level must be 1, 2, or 3")


@dataclass(frozen=True, slots=True)
class RequirementMatch:
    requirement: AsvsRequirement
    score: float
