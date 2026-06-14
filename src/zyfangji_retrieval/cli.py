from pathlib import Path

import typer

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import RowIssue, build_import_report


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
def import_excel(path: Path, dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run")) -> None:
    if not dry_run:
        raise typer.BadParameter("persistent import is implemented in Plan 03")

    workbook_rows = read_shanghanlun_workbook(path)
    entries, issues = _map_workbook(path)
    report = build_import_report(
        workbook_rows,
        entries,
        issues,
        index_version="dry-run",
    )
    typer.echo(report.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
