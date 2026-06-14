from pathlib import Path

import pandas as pd
import pytest

from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.retrieval_text import SOURCE_HEADERS


SAMPLE_WORKBOOK = Path("data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx")


def _write_workbook(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    title = ["伤寒论病症信息对应表"] + [""] * (len(headers) - 1)
    group_header = ["基础信息"] + [""] * (len(headers) - 1)
    df = pd.DataFrame([title, group_header, headers, *rows])
    df.to_excel(path, header=False, index=False)


def test_read_real_workbook_reports_exact_source_headers() -> None:
    workbook = read_shanghanlun_workbook(SAMPLE_WORKBOOK)

    assert len(workbook.headers) == 22
    assert workbook.headers == SOURCE_HEADERS


def test_real_workbook_uses_excel_row_3_header_and_row_4_first_data() -> None:
    workbook = read_shanghanlun_workbook(SAMPLE_WORKBOOK)

    assert workbook.rows[0].source_row == 4
    assert workbook.rows[0].source_sheet
    assert workbook.rows[0].raw_record["主病主症"] == "头痛"
    assert workbook.rows[0].raw_record["推荐方剂"] == "麻黄汤"


def test_header_drift_raises_value_error(tmp_path: Path) -> None:
    workbook_path = tmp_path / "bad_headers.xlsx"
    reordered_headers = [SOURCE_HEADERS[1], SOURCE_HEADERS[0], *SOURCE_HEADERS[2:]]
    _write_workbook(workbook_path, reordered_headers, [[""] * len(SOURCE_HEADERS)])

    with pytest.raises(ValueError, match="Expected 22 source headers"):
        read_shanghanlun_workbook(workbook_path)


def test_blank_rows_are_skipped_from_emitted_rows(tmp_path: Path) -> None:
    workbook_path = tmp_path / "blank_rows.xlsx"
    valid_row = [""] * len(SOURCE_HEADERS)
    valid_row[SOURCE_HEADERS.index("主病主症")] = "头痛"
    valid_row[SOURCE_HEADERS.index("推荐方剂")] = "麻黄汤"
    blank_row = [""] * len(SOURCE_HEADERS)
    _write_workbook(workbook_path, SOURCE_HEADERS, [valid_row, blank_row])

    workbook = read_shanghanlun_workbook(workbook_path)

    assert [row.source_row for row in workbook.rows] == [4]
    assert workbook.rows[0].raw_record["主病主症"] == "头痛"
