from pathlib import Path

import pandas as pd
import pytest

from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
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


def test_valid_workbook_row_maps_to_knowledge_entry_with_all_raw_columns() -> None:
    row = read_shanghanlun_workbook(SAMPLE_WORKBOOK).rows[0]

    entry = map_row_to_entry(row)

    assert entry is not None
    assert len(entry.raw_record) == 22
    assert entry.normalized_record["main_symptom"] == "头痛"
    assert entry.formula_raw == "麻黄汤"
    assert entry.source_code is None


def test_entry_id_is_stable_and_not_source_code() -> None:
    row = read_shanghanlun_workbook(SAMPLE_WORKBOOK).rows[0]

    first_entry = map_row_to_entry(row)
    second_entry = map_row_to_entry(row)

    assert first_entry is not None
    assert second_entry is not None
    assert first_entry.entry_id == second_entry.entry_id
    assert first_entry.entry_id != row.raw_record["编码"]


def test_missing_searchable_text_skips_row_with_issue_code() -> None:
    row = read_shanghanlun_workbook(SAMPLE_WORKBOOK).rows[0]
    raw_record = dict.fromkeys(SOURCE_HEADERS, "")
    raw_record["推荐方剂"] = "麻黄汤"
    raw_record["伤寒论原文条文号"] = "第 35 条"
    empty_search_row = type(row)(
        source_sheet=row.source_sheet,
        source_row=999,
        raw_record=raw_record,
    )

    issues = validate_source_row(empty_search_row)

    assert map_row_to_entry(empty_search_row) is None
    assert [issue.code for issue in issues] == ["missing_searchable_text"]


def test_missing_formula_raw_skips_row_with_issue_code() -> None:
    row = read_shanghanlun_workbook(SAMPLE_WORKBOOK).rows[0]
    raw_record = dict.fromkeys(SOURCE_HEADERS, "")
    raw_record["主病主症"] = "头痛"
    raw_record["伤寒论原文条文号"] = "第 35 条"
    missing_formula_row = type(row)(
        source_sheet=row.source_sheet,
        source_row=1000,
        raw_record=raw_record,
    )

    issues = validate_source_row(missing_formula_row)

    assert map_row_to_entry(missing_formula_row) is None
    assert [issue.code for issue in issues] == ["missing_formula_raw"]
