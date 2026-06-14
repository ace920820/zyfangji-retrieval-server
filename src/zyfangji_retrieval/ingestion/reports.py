from typing import Literal

from pydantic import BaseModel

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import WorkbookRows


class RowIssue(BaseModel):
    source_row: int
    code: str
    message: str
    severity: Literal["warning", "error"]


class ImportReport(BaseModel):
    source_file: str
    source_sheet: str
    total_rows: int
    valid_rows: int
    skipped_rows: int
    warning_count: int
    failed_rows: list[RowIssue]
    indexed_count: int
    index_version: str
    metadata_version: str = "local-v1"


def build_import_report(
    workbook_rows: WorkbookRows,
    entries: list[KnowledgeEntry],
    issues: list[RowIssue],
    index_version: str,
) -> ImportReport:
    failed_rows = [issue for issue in issues if issue.severity == "error"]
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    failed_source_rows = {issue.source_row for issue in failed_rows}
    skipped_rows = workbook_rows.blank_rows + len(failed_source_rows)

    return ImportReport(
        source_file=workbook_rows.source_file,
        source_sheet=workbook_rows.source_sheet,
        total_rows=len(workbook_rows.rows) + workbook_rows.blank_rows,
        valid_rows=len(entries),
        skipped_rows=skipped_rows,
        warning_count=warning_count,
        failed_rows=failed_rows,
        indexed_count=len(entries),
        index_version=index_version,
    )
