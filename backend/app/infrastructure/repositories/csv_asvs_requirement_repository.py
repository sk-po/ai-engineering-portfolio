import csv
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from app.domain.models.asvs_requirement import AsvsRequirement, RequirementMatch

_LATIN_TOKEN = re.compile(r"[a-z0-9][a-z0-9._/-]+")
_JAPANESE_SEQUENCE = re.compile(r"[\u3040-\u30ff\u3400-\u9fffー]+")
_QUERY_EXPANSIONS = (
    (("保存", "保管", "格納"), "ハッシュ password storage key derivation"),
    (("ログイン", "認証"), "authentication identity"),
    (("権限", "認可"), "authorization access control"),
    (("アップロード",), "file upload ファイル"),
)
_SEMANTIC_BOOSTS = (
    (("保存", "保管", "格納"), ("ハッシュ", "storage", "key derivation")),
    (("認可", "権限"), ("authorization", "access control")),
    (("アップロード",), ("file upload", "アップロード")),
)


class CsvAsvsRequirementRepository:
    def __init__(self, english_path: Path, japanese_path: Path) -> None:
        self._requirements = self._load_requirements(english_path, japanese_path)
        self._document_texts = tuple(
            _searchable_text(requirement) for requirement in self._requirements
        )
        self._document_features = tuple(
            _features(document_text) for document_text in self._document_texts
        )
        document_frequency: Counter[str] = Counter()
        for features in self._document_features:
            document_frequency.update(features.keys())
        document_count = len(self._requirements)
        self._idf = {
            feature: math.log((document_count + 1) / (frequency + 1)) + 1
            for feature, frequency in document_frequency.items()
        }
        self._document_norms = tuple(
            _weighted_norm(features, self._idf)
            for features in self._document_features
        )

    def list_all(self) -> tuple[AsvsRequirement, ...]:
        return self._requirements

    def search(
        self, query: str, *, level: int | None, limit: int
    ) -> tuple[RequirementMatch, ...]:
        query_features = _features(_expand_query(query))
        query_norm = _weighted_norm(query_features, self._idf)
        normalized_query = _normalize(query)
        matches: list[RequirementMatch] = []

        for requirement, document_text, features, document_norm in zip(
            self._requirements,
            self._document_texts,
            self._document_features,
            self._document_norms,
            strict=True,
        ):
            if level is not None and requirement.level > level:
                continue
            score = _cosine_score(
                query_features,
                features,
                self._idf,
                query_norm,
                document_norm,
            )
            score += _semantic_boost(query, document_text)
            if normalized_query == requirement.requirement_id.casefold():
                score = 1.0
            if score > 0:
                matches.append(RequirementMatch(requirement, round(score, 4)))

        matches.sort(
            key=lambda match: (
                -match.score,
                match.requirement.level,
                match.requirement.requirement_id,
            )
        )
        return tuple(matches[:limit])

    @staticmethod
    def _load_requirements(
        english_path: Path, japanese_path: Path
    ) -> tuple[AsvsRequirement, ...]:
        english_rows = _read_rows(english_path)
        japanese_rows = _read_rows(japanese_path)
        english_by_id = {row["req_id"]: row for row in english_rows}
        japanese_by_id = {row["req_id"]: row for row in japanese_rows}

        if english_by_id.keys() != japanese_by_id.keys():
            raise ValueError("English and Japanese ASVS requirement IDs differ")

        return tuple(
            AsvsRequirement(
                requirement_id=requirement_id,
                chapter_id=english["chapter_id"],
                chapter_name_ja=japanese["chapter_name"],
                chapter_name_en=english["chapter_name"],
                section_id=english["section_id"],
                section_name_ja=japanese["section_name"],
                section_name_en=english["section_name"],
                description_ja=japanese["req_description"],
                description_en=english["req_description"],
                level=int(english["L"]),
            )
            for requirement_id, english in english_by_id.items()
            for japanese in (japanese_by_id[requirement_id],)
        )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _features(value: str) -> Counter[str]:
    normalized = _normalize(value)
    features: Counter[str] = Counter()
    for token in _LATIN_TOKEN.findall(normalized):
        features[f"latin:{token}"] += 2
    for sequence in _JAPANESE_SEQUENCE.findall(normalized):
        for size, weight in ((2, 1), (3, 2)):
            for index in range(max(0, len(sequence) - size + 1)):
                features[f"ja{size}:{sequence[index:index + size]}"] += weight
    return features


def _expand_query(value: str) -> str:
    normalized = _normalize(value)
    expansions = [
        expansion
        for triggers, expansion in _QUERY_EXPANSIONS
        if any(trigger in normalized for trigger in triggers)
    ]
    return " ".join((value, *expansions))


def _semantic_boost(query: str, document: str) -> float:
    normalized_query = _normalize(query)
    normalized_document = _normalize(document)
    boost = 0.0
    for triggers, indicators in _SEMANTIC_BOOSTS:
        if any(trigger in normalized_query for trigger in triggers):
            boost += 0.12 * sum(
                indicator in normalized_document for indicator in indicators
            )
    return boost


def _searchable_text(requirement: AsvsRequirement) -> str:
    return " ".join(
        (
            requirement.requirement_id,
            requirement.chapter_id,
            requirement.chapter_name_ja,
            requirement.chapter_name_en,
            requirement.section_id,
            requirement.section_name_ja,
            requirement.section_name_en,
            requirement.description_ja,
            requirement.description_en,
        )
    )


def _weighted_norm(features: Counter[str], idf: dict[str, float]) -> float:
    return math.sqrt(
        sum(
            (count * idf.get(feature, 1.0)) ** 2
            for feature, count in features.items()
        )
    )


def _cosine_score(
    query: Counter[str],
    document: Counter[str],
    idf: dict[str, float],
    query_norm: float,
    document_norm: float,
) -> float:
    if not query_norm or not document_norm:
        return 0.0
    dot_product = sum(
        count
        * document.get(feature, 0)
        * idf.get(feature, 1.0) ** 2
        for feature, count in query.items()
    )
    return dot_product / (query_norm * document_norm)
