import unittest
from collections.abc import Sequence
from pathlib import Path

from app.application.models import EmbeddedAsvsIndexDocument
from app.application.use_cases import IndexAsvsDocuments
from app.domain.models import AsvsRequirement
from app.infrastructure.files.csv_asvs_requirement_repository import (
    CsvAsvsRequirementRepository,
)


def _requirement(number: int = 1) -> AsvsRequirement:
    return AsvsRequirement(
        requirement_id=f"V1.1.{number}",
        chapter_id="V1",
        chapter_name_ja="エンコーディングとサニタイゼーション",
        chapter_name_en="Encoding and Sanitization",
        section_id="V1.1",
        section_name_ja="アーキテクチャ",
        section_name_en="Architecture",
        description_ja=f"日本語の要件 {number}",
        description_en=f"English requirement {number}",
        level=2,
    )


class FakeSource:
    def __init__(self, requirements: tuple[AsvsRequirement, ...]) -> None:
        self.requirements = requirements

    def list_all(self) -> tuple[AsvsRequirement, ...]:
        return self.requirements


class FakeEmbeddingClient:
    def __init__(self, dimensions: int) -> None:
        """指定次元数の固定Embeddingを返すテストクライアントを初期化する。

        Args:
            dimensions: 1件ごとに返すベクトルの次元数。
        """
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """入力文を記録し、各入力に固定値のベクトルを返す。

        Args:
            texts: ベクトル化対象として渡された文章列。

        Returns:
            入力件数と設定次元数に対応する固定ベクトル。
        """
        self.calls.append(list(texts))
        return tuple(tuple(0.1 for _ in range(self.dimensions)) for _ in texts)


class FakeWriter:
    def __init__(self) -> None:
        """書き込み呼び出しを保持するテストwriterを初期化する。"""
        self.calls: list[tuple[EmbeddedAsvsIndexDocument, ...]] = []

    def merge_or_upload(self, documents: Sequence[EmbeddedAsvsIndexDocument]) -> int:
        """受け取った文書を記録し、その件数を成功数として返す。

        Args:
            documents: 登録対象として渡されたEmbedding付き文書列。

        Returns:
            受け取った文書件数。
        """
        self.calls.append(tuple(documents))
        return len(documents)


class IndexAsvsDocumentsTestCase(unittest.TestCase):
    def test_prepares_all_pinned_asvs_requirements(self) -> None:
        backend_dir = Path(__file__).resolve().parents[2]
        data_dir = backend_dir / "app" / "infrastructure" / "data"
        source = CsvAsvsRequirementRepository(
            data_dir / "asvs-5.0.0-en.csv",
            data_dir / "asvs-5.0.0-ja.csv",
        )

        documents = IndexAsvsDocuments(source).prepare()

        self.assertEqual(len(documents), 345)
        self.assertEqual(len({item.chunk_id for item in documents}), 345)
        self.assertTrue(all("." not in item.chunk_id for item in documents))

    def test_prepares_one_deterministic_chunk_per_requirement(self) -> None:
        source = FakeSource((_requirement(),))
        use_case = IndexAsvsDocuments(source, expected_source_count=1)

        first = use_case.prepare()[0]
        second = use_case.prepare()[0]

        self.assertEqual(first, second)
        self.assertEqual(first.chunk_id, "asvs-5-0-0-v1-1-1")
        self.assertEqual(first.requirement_id, "V1.1.1")
        self.assertIn("Japanese: 日本語の要件 1", first.content)
        self.assertIn("English: English requirement 1", first.content)

    def test_embeds_and_writes_in_batches(self) -> None:
        source = FakeSource(tuple(_requirement(number) for number in range(1, 4)))
        embedder = FakeEmbeddingClient(dimensions=3)
        writer = FakeWriter()
        progress = []
        use_case = IndexAsvsDocuments(
            source,
            embedder,
            writer,
            vector_dimensions=3,
            batch_size=2,
            expected_source_count=3,
            on_batch_completed=lambda batch, indexed, total: progress.append(
                (batch, indexed, total)
            ),
        )

        summary = use_case.execute()

        self.assertEqual(summary.source_count, 3)
        self.assertEqual(summary.indexed_count, 3)
        self.assertEqual(summary.batch_count, 2)
        self.assertEqual([len(call) for call in embedder.calls], [2, 1])
        self.assertEqual([len(call) for call in writer.calls], [2, 1])
        self.assertEqual(progress, [(1, 2, 3), (2, 3, 3)])

    def test_rejects_vector_dimension_mismatch_before_writing(self) -> None:
        source = FakeSource((_requirement(),))
        embedder = FakeEmbeddingClient(dimensions=2)
        writer = FakeWriter()
        use_case = IndexAsvsDocuments(
            source,
            embedder,
            writer,
            vector_dimensions=3,
            expected_source_count=1,
        )

        with self.assertRaisesRegex(ValueError, "dimensions"):
            use_case.execute()

        self.assertEqual(writer.calls, [])

    def test_rejects_incomplete_source_before_limit_is_applied(self) -> None:
        use_case = IndexAsvsDocuments(
            FakeSource((_requirement(),)), expected_source_count=345
        )

        with self.assertRaisesRegex(ValueError, "expected 345, got 1"):
            use_case.prepare(limit=1)


if __name__ == "__main__":
    unittest.main()
