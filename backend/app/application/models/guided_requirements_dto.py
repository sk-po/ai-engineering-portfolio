from dataclasses import dataclass
from typing import Literal

from app.domain.models import RequirementMatch


@dataclass(frozen=True, slots=True)
class GuidedRequirementsDecision:
    """要件ヒアリングで次に行う操作を表す。"""

    action: Literal["ask", "complete"]
    question: str | None
    missing_topics: tuple[str, ...]
    retrieval_queries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GuidedRequirementsResult:
    """1ターン分のヒアリング結果と、完了時のRAG根拠を表す。"""

    action: Literal["ask", "complete"]
    question: str | None
    missing_topics: tuple[str, ...]
    answer: str | None
    sources: tuple[RequirementMatch, ...]
    turn: int
