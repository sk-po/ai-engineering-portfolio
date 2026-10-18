from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AsvsIndexDocument:
    chunk_id: str
    document_id: str
    title: str
    section: str
    content: str
    source_uri: str
    source_name: str
    document_type: str
    category: str
    tags: tuple[str, ...]
    language: str
    version: str
    updated_at: datetime
    security_level: str
    allowed_group_ids: tuple[str, ...]
    security_domain: str
    control_ids: tuple[str, ...]
    content_status: str
    effective_from: datetime
    framework_name: str
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
    translation_status: str
    official_english_source: str
    japanese_translation_source: str


@dataclass(frozen=True, slots=True)
class EmbeddedAsvsIndexDocument:
    document: AsvsIndexDocument
    content_vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class IndexingSummary:
    source_count: int
    indexed_count: int
    batch_count: int
