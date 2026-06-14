from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from zyfangji_retrieval.ingestion.retrieval_text import SOURCE_HEADERS


@dataclass(frozen=True)
class WorkbookRow:
    source_sheet: str
    source_row: int
    raw_record: dict[str, str]


@dataclass(frozen=True)
class WorkbookRows:
    source_file: str
    source_sheet: str
    headers: list[str]
    rows: list[WorkbookRow]
    blank_rows: int = 0


def read_shanghanlun_workbook(path: Path, sheet_name: str | int | None = 0) -> WorkbookRows:
    if not isinstance(path, Path):
        raise TypeError("read_shanghanlun_workbook expects a local pathlib.Path")

    selected_sheet = 0 if sheet_name is None else sheet_name
    excel_file = pd.ExcelFile(path)
    resolved_sheet = (
        excel_file.sheet_names[selected_sheet]
        if isinstance(selected_sheet, int)
        else str(selected_sheet)
    )
    df = pd.read_excel(
        path,
        sheet_name=selected_sheet,
        header=2,
        dtype=str,
        keep_default_na=False,
    )
    df.columns = [str(column).strip() for column in df.columns]
    headers = list(df.columns)
    if headers != SOURCE_HEADERS:
        raise ValueError(
            f"Expected 22 source headers matching SOURCE_HEADERS; got {len(headers)} headers"
        )

    rows: list[WorkbookRow] = []
    blank_rows = 0
    for index, record in df.iterrows():
        raw_record = {
            header: str(record.get(header, "")).strip()
            for header in SOURCE_HEADERS
        }
        if not any(raw_record.values()):
            blank_rows += 1
            continue
        source_row = int(index) + 4
        rows.append(
            WorkbookRow(
                source_sheet=resolved_sheet,
                source_row=source_row,
                raw_record=raw_record,
            )
        )

    return WorkbookRows(
        source_file=str(path),
        source_sheet=resolved_sheet,
        headers=headers,
        rows=rows,
        blank_rows=blank_rows,
    )
