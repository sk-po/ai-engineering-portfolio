from dataclasses import dataclass

from app.domain.models import RequirementMatch


@dataclass(frozen=True, slots=True)
class GeneratedRequirementAnswer:
    """生成された回答と、その根拠として検索されたASVS要件。"""

    answer: str
    sources: tuple[RequirementMatch, ...]
