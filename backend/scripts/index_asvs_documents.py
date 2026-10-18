import argparse
import sys
from pathlib import Path

"""
AzureAIIndexにASVSドキュメントを登録するバッチスクリプト
実行方法は、backend/scripts/README.md
を参照

"""


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.application.use_cases import IndexAsvsDocuments  # noqa: E402
from app.infrastructure.files.csv_asvs_requirement_repository import (  # noqa: E402
    CsvAsvsRequirementRepository,
)
from app.settings import AzureSearchSettings  # noqa: E402

DATA_DIR = BACKEND_DIR / "app" / "infrastructure" / "data"
DEFAULT_ENGLISH_CSV = DATA_DIR / "asvs-5.0.0-en.csv"
DEFAULT_JAPANESE_CSV = DATA_DIR / "asvs-5.0.0-ja.csv"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create one chunk per ASVS requirement, generate embeddings, and "
            "merge or upload documents to Azure AI Search."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call Azure and update the index. Without this flag, only validate and preview.",
    )
    parser.add_argument("--limit", type=int, help="Process only the first N documents.")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--english-csv", type=Path, default=DEFAULT_ENGLISH_CSV)
    parser.add_argument("--japanese-csv", type=Path, default=DEFAULT_JAPANESE_CSV)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source = CsvAsvsRequirementRepository(args.english_csv, args.japanese_csv)

    if not args.execute:
        use_case = IndexAsvsDocuments(source, batch_size=args.batch_size)
        documents = use_case.prepare(limit=args.limit)
        print(
            f"Dry run succeeded: {len(documents)} documents prepared; Azure was not called."
        )
        if documents:
            print(f"First chunk: {documents[0].chunk_id}")
            print(f"Last chunk: {documents[-1].chunk_id}")
        print("Add --execute to generate embeddings and update Azure AI Search.")
        return 0

    settings = AzureSearchSettings()

    from azure.identity import DefaultAzureCredential

    from app.infrastructure.external import (
        AzureOpenAIEmbeddingClient,
        AzureSearchDocumentWriter,
    )

    credential = DefaultAzureCredential()
    embedding_client = AzureOpenAIEmbeddingClient(
        base_url=str(settings.openai_base_url),
        deployment_name=settings.embedding_deployment,
        credential=credential,
        on_rate_limit=lambda attempt, seconds: print(
            "Embedding rate limit reached; "
            f"waiting {seconds:g} seconds before retry {attempt}/10...",
            flush=True,
        ),
    )
    document_writer = AzureSearchDocumentWriter(
        endpoint=str(settings.search_endpoint).rstrip("/"),
        index_name=settings.search_index_name,
        credential=credential,
    )
    use_case = IndexAsvsDocuments(
        source,
        embedding_client,
        document_writer,
        batch_size=args.batch_size,
        on_batch_completed=lambda batch, indexed, total: print(
            f"Progress: batch {batch}, {indexed}/{total} documents indexed.",
            flush=True,
        ),
    )
    summary = use_case.execute(limit=args.limit)
    print(
        "Indexing succeeded: "
        f"{summary.indexed_count}/{summary.source_count} documents in "
        f"{summary.batch_count} batches."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
