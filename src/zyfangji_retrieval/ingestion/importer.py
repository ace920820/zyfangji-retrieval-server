from datetime import UTC, datetime
from pathlib import Path

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import ImportReport, RowIssue, build_import_report
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore


def _local_index_version(store: SQLiteMetadataStore) -> str:
    base = "local-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    with store.connect() as connection:
        existing = connection.execute(
            "select batch_id from import_batches where batch_id = ?",
            (base,),
        ).fetchone()
        if existing is None:
            return base
        count = connection.execute(
            "select count(*) from import_batches where batch_id like ?",
            (f"{base}%",),
        ).fetchone()[0]
    return f"{base}-{count + 1:02d}"


def import_workbook_to_metadata(
    workbook_path: Path,
    db_path: Path,
    source_book: str = "伤寒论",
) -> ImportReport:
    workbook_rows = read_shanghanlun_workbook(workbook_path)
    entries: list[KnowledgeEntry] = []
    issues: list[RowIssue] = []
    for row in workbook_rows.rows:
        row_issues = validate_source_row(row)
        issues.extend(row_issues)
        if any(issue.severity == "error" for issue in row_issues):
            continue
        entry = map_row_to_entry(row)
        if entry is not None:
            if entry.source_book != source_book:
                entry = entry.model_copy(update={"source_book": source_book})
            entries.append(entry)

    store = SQLiteMetadataStore(db_path)
    index_version = _local_index_version(store)
    report = build_import_report(
        workbook_rows,
        entries,
        issues,
        index_version=index_version,
    )
    report = report.model_copy(update={"indexed_count": len(entries)})
    store.save_import(
        batch_id=index_version,
        report=report,
        entries=entries,
        raw_rows=workbook_rows.rows,
        issues=issues,
    )
    return report


def load_entries_for_rebuild(
    db_path: Path,
    index_version: str | None = None,
) -> list[KnowledgeEntry]:
    return SQLiteMetadataStore(db_path).load_entries(index_version=index_version)
