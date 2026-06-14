import json
from pathlib import Path

import typer

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.importer import (
    import_workbook_to_metadata,
    load_entries_for_rebuild,
)
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import RowIssue, build_import_report
from zyfangji_retrieval.persistence.jsonl import export_entries_jsonl
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore


app = typer.Typer(no_args_is_help=True)


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
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
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


if __name__ == "__main__":
    app()
