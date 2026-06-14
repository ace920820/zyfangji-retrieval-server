import json
from pathlib import Path

import typer
from qdrant_client import QdrantClient

from zyfangji_retrieval.config import get_settings
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.indexing.bm25_store import BM25IndexStore
from zyfangji_retrieval.indexing.embeddings import DeterministicEmbeddingProvider
from zyfangji_retrieval.indexing.lifecycle import IndexLifecycleService
from zyfangji_retrieval.indexing.qdrant_store import QdrantVectorIndex
from zyfangji_retrieval.indexing.status import IndexStatusService
from zyfangji_retrieval.indexing.validation import validate_persisted_counts
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.importer import (
    import_workbook_to_metadata,
    load_entries_for_rebuild,
)
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import RowIssue, build_import_report
from zyfangji_retrieval.persistence.jsonl import export_entries_jsonl
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore


app = typer.Typer(no_args_is_help=True)


class LocalQdrantVectorIndex(QdrantVectorIndex):
    def __init__(self, collection_prefix: str, alias_name: str, vector_size: int) -> None:
        super().__init__(
            client=QdrantClient(":memory:"),
            collection_prefix=collection_prefix,
            alias_name=alias_name,
            vector_size=vector_size,
        )

    def activate_alias(self, index_version: str) -> str:
        self.collection_name(index_version)
        return self.alias_name


def _map_workbook(path: Path) -> tuple[list[KnowledgeEntry], list[RowIssue]]:
    workbook_rows = read_shanghanlun_workbook(path)
    entries: list[KnowledgeEntry] = []
    issues: list[RowIssue] = []
    for row in workbook_rows.rows:
        row_issues = validate_source_row(row)
        issues.extend(row_issues)
        if any(issue.severity == "error" for issue in row_issues):
            continue
        entry = map_row_to_entry(row)
        if entry is not None:
            entries.append(entry)
    return entries, issues


@app.command("inspect-workbook")
def inspect_workbook(path: Path) -> None:
    workbook_rows = read_shanghanlun_workbook(path)
    typer.echo(f"Source file: {workbook_rows.source_file}")
    typer.echo(f"Sheet name: {workbook_rows.source_sheet}")
    typer.echo(f"Header count: {len(workbook_rows.headers)}")
    typer.echo(f"Row count: {len(workbook_rows.rows)}")
    typer.echo(f"Blank rows: {workbook_rows.blank_rows}")


@app.command("import-excel")
def import_excel(
    path: Path,
    dry_run: bool = typer.Option(False, "--dry-run/--no-dry-run"),
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    jsonl_export: Path | None = typer.Option(None, "--jsonl-export"),
) -> None:
    if dry_run:
        workbook_rows = read_shanghanlun_workbook(path)
        entries, issues = _map_workbook(path)
        report = build_import_report(
            workbook_rows,
            entries,
            issues,
            index_version="dry-run",
        )
    else:
        report = import_workbook_to_metadata(path, db_path)
        if jsonl_export is not None:
            entries = load_entries_for_rebuild(db_path, index_version=report.index_version)
            export_entries_jsonl(entries, jsonl_export)
    typer.echo(report.model_dump_json(indent=2, ensure_ascii=False))


@app.command("rebuild-source")
def rebuild_source(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    index_version: str | None = typer.Option(None, "--index-version"),
) -> None:
    entries = load_entries_for_rebuild(db_path, index_version=index_version)
    latest_batch = SQLiteMetadataStore(db_path).latest_batch()
    resolved_index_version = index_version
    if resolved_index_version is None and latest_batch is not None:
        resolved_index_version = str(latest_batch["index_version"])
    source = "local_metadata"
    typer.echo(
        json.dumps(
            {
                "entry_count": len(entries),
                "index_version": resolved_index_version,
                "source": source,
            },
            ensure_ascii=False,
        )
    )


def _latest_metadata_version(db_path: Path, metadata_version: str | None) -> str:
    if metadata_version is not None:
        return metadata_version
    latest_batch = SQLiteMetadataStore(db_path).latest_batch()
    if latest_batch is None:
        raise typer.BadParameter("metadata database has no import batch")
    return str(latest_batch["index_version"])


@app.command("index-rebuild")
def index_rebuild(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    metadata_version: str | None = typer.Option(None, "--metadata-version"),
    bm25_index_root: Path = typer.Option(Path("var/indexes/bm25"), "--bm25-index-root"),
    activate: bool = typer.Option(True, "--activate/--no-activate"),
) -> None:
    settings = get_settings()
    provider = DeterministicEmbeddingProvider(vector_size=settings.embedding_vector_size)
    qdrant_index = LocalQdrantVectorIndex(
        collection_prefix=settings.qdrant_collection_prefix,
        alias_name=settings.qdrant_alias,
        vector_size=provider.vector_size,
    )
    state_store = SQLiteIndexStateStore(db_path)
    service = IndexLifecycleService(
        db_path=db_path,
        metadata_version=_latest_metadata_version(db_path, metadata_version),
        embedding_provider=provider,
        qdrant_index=qdrant_index,
        bm25_store=BM25IndexStore(bm25_index_root),
        index_state_store=state_store,
    )
    record = service.rebuild(activate=activate)
    typer.echo(record.model_dump_json(indent=2, ensure_ascii=False))


@app.command("index-validate")
def index_validate(
    index_version: str = typer.Option(..., "--index-version"),
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    bm25_index_root: Path = typer.Option(Path("var/indexes/bm25"), "--bm25-index-root"),
) -> None:
    state_store = SQLiteIndexStateStore(db_path)
    build = state_store.get_build(index_version)
    if build is None:
        raise typer.BadParameter(f"index build does not exist: {index_version}")
    bm25_result = BM25IndexStore(bm25_index_root).validate(
        index_version,
        expected_count=build.entry_count,
    )
    validation = validate_persisted_counts(
        index_version=index_version,
        expected_count=build.entry_count,
        vector_count=build.vector_count,
        bm25_result=bm25_result,
        qdrant_collection=build.qdrant_collection,
        qdrant_alias=build.qdrant_alias,
    )
    typer.echo(validation.model_dump_json(indent=2, ensure_ascii=False))


@app.command("index-status")
def index_status(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
) -> None:
    settings = get_settings()
    state_store = SQLiteIndexStateStore(db_path)
    status = IndexStatusService(state_store, settings).status()
    typer.echo(status.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
