import json
import sqlite3
from pathlib import Path

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import WorkbookRow, read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.importer import (
    import_workbook_to_metadata,
    load_entries_for_rebuild,
)
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import ImportReport, RowIssue, build_import_report
from zyfangji_retrieval.persistence.jsonl import export_entries_jsonl, load_entries_jsonl
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore


SAMPLE_WORKBOOK = Path("data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx")


def _sample_row_and_entry() -> tuple[WorkbookRow, KnowledgeEntry]:
    row = read_shanghanlun_workbook(SAMPLE_WORKBOOK).rows[0]
    entry = map_row_to_entry(row)
    assert entry is not None
    return row, entry


def _sample_report(entry: KnowledgeEntry) -> ImportReport:
    return ImportReport(
        source_file=str(SAMPLE_WORKBOOK),
        source_sheet=entry.source_sheet,
        total_rows=1,
        valid_rows=1,
        skipped_rows=0,
        warning_count=1,
        failed_rows=[],
        indexed_count=1,
        index_version="local-test",
    )


def test_sqlite_metadata_store_creates_required_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    SQLiteMetadataStore(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert {
        "import_batches",
        "raw_records",
        "knowledge_entries",
        "row_issues",
    } <= table_names


def test_save_import_can_load_entry_by_id_and_latest_batch(tmp_path: Path) -> None:
    row, entry = _sample_row_and_entry()
    report = _sample_report(entry)
    warning = RowIssue(
        source_row=row.source_row,
        code="formula_needs_review",
        severity="warning",
        message="review formula text",
    )
    store = SQLiteMetadataStore(tmp_path / "metadata.db")

    store.save_import(
        batch_id="local-test",
        report=report,
        entries=[entry],
        raw_rows=[row],
        issues=[warning],
    )

    loaded = store.load_entry(entry.entry_id)
    latest_batch = store.latest_batch()

    assert loaded == entry
    assert latest_batch is not None
    assert latest_batch["batch_id"] == "local-test"
    assert latest_batch["metadata_version"] == "local-v1"


def test_save_import_upserts_entry_without_duplicate_and_updates_timestamp(
    tmp_path: Path,
) -> None:
    row, entry = _sample_row_and_entry()
    report = _sample_report(entry)
    store = SQLiteMetadataStore(tmp_path / "metadata.db")

    store.save_import("local-first", report, [entry], [row], [])
    with store.connect() as connection:
        first = connection.execute(
            "select created_at, updated_at from knowledge_entries where entry_id = ?",
            (entry.entry_id,),
        ).fetchone()

    updated_entry = entry.model_copy(update={"retrieval_text": entry.retrieval_text + "\n复核"})
    updated_report = report.model_copy(update={"index_version": "local-second"})
    store.save_import("local-second", updated_report, [updated_entry], [row], [])

    with store.connect() as connection:
        rows = connection.execute(
            "select created_at, updated_at, retrieval_text from knowledge_entries where entry_id = ?",
            (entry.entry_id,),
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["created_at"] == first["created_at"]
    assert rows[0]["updated_at"] >= first["updated_at"]
    assert rows[0]["retrieval_text"].endswith("复核")


def test_raw_records_are_queryable_by_source_row_and_preserve_all_source_fields(
    tmp_path: Path,
) -> None:
    row, entry = _sample_row_and_entry()
    workbook_rows = read_shanghanlun_workbook(SAMPLE_WORKBOOK)
    issues = validate_source_row(row)
    report = build_import_report(workbook_rows, [entry], issues, index_version="local-test")
    store = SQLiteMetadataStore(tmp_path / "metadata.db")

    store.save_import("local-test", report, [entry], [row], issues)

    with store.connect() as connection:
        raw_record = connection.execute(
            "select raw_json from raw_records where source_row = ?",
            (row.source_row,),
        ).fetchone()

    assert raw_record is not None
    payload = json.loads(raw_record["raw_json"])
    assert payload["推荐方剂"] == "麻黄汤"
    assert len(payload) == 22


def test_import_workbook_to_metadata_persists_real_workbook_report(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    report = import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)

    assert report.total_rows > 1200
    assert report.valid_rows > 1000
    assert report.indexed_count == report.valid_rows
    assert report.index_version.startswith("local-")
    assert report.metadata_version == "local-v1"


def test_load_entries_for_rebuild_returns_persisted_entry_count(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    report = import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)

    entries = load_entries_for_rebuild(db_path)

    assert len(entries) == report.indexed_count
    assert all(entry.entry_id for entry in entries)


def test_reimporting_same_workbook_preserves_entry_id_set(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    first_report = import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)
    first_ids = {entry.entry_id for entry in load_entries_for_rebuild(db_path)}
    second_report = import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)
    second_ids = {entry.entry_id for entry in load_entries_for_rebuild(db_path)}

    assert first_report.index_version.startswith("local-")
    assert second_report.index_version.startswith("local-")
    assert first_ids == second_ids
    assert len(second_ids) == second_report.indexed_count


def test_local_persistence_import_does_not_require_customer_mysql() -> None:
    import zyfangji_retrieval.ingestion.importer as importer

    source = Path(importer.__file__).read_text(encoding="utf-8")
    banned_terms = (
        "MY" + "SQL",
        "My" + "SQL",
        "py" + "mysql",
        "SQL" + "Alchemy",
    )

    assert all(term not in source for term in banned_terms)


def test_jsonl_export_writes_utf8_lines_and_preserves_chinese(tmp_path: Path) -> None:
    _, entry = _sample_row_and_entry()
    export_path = tmp_path / "entries.jsonl"

    export_entries_jsonl([entry], export_path)

    content = export_path.read_text(encoding="utf-8")
    assert content.count("\n") == 1
    assert "麻黄汤" in content
    assert json.loads(content)["entry_id"] == entry.entry_id


def test_jsonl_load_round_trips_knowledge_entries(tmp_path: Path) -> None:
    _, entry = _sample_row_and_entry()
    export_path = tmp_path / "entries.jsonl"

    export_entries_jsonl([entry], export_path)
    loaded = load_entries_jsonl(export_path)

    assert loaded == [entry]


def test_import_excel_cli_persists_entries_and_prints_metadata_version(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "metadata.db"
    result = runner.invoke(
        app,
        [
            "import-excel",
            str(SAMPLE_WORKBOOK),
            "--no-dry-run",
            "--db-path",
            str(db_path),
        ],
        catch_exceptions=False,
    )

    entries = load_entries_for_rebuild(db_path)

    assert result.exit_code == 0
    assert '"metadata_version": "local-v1"' in result.output
    assert len(entries) > 1000


def test_import_excel_cli_can_export_jsonl(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    export_path = tmp_path / "entries.jsonl"

    result = runner.invoke(
        app,
        [
            "import-excel",
            str(SAMPLE_WORKBOOK),
            "--no-dry-run",
            "--db-path",
            str(db_path),
            "--jsonl-export",
            str(export_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert len(load_entries_jsonl(export_path)) > 1000


def test_rebuild_source_cli_prints_local_metadata_count_without_workbook_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "metadata.db"
    report = import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)

    def fail_if_called(path: Path) -> object:
        raise AssertionError(f"unexpected workbook parse: {path}")

    monkeypatch.setattr("zyfangji_retrieval.cli.read_shanghanlun_workbook", fail_if_called)

    result = runner.invoke(
        app,
        ["rebuild-source", "--db-path", str(db_path)],
        catch_exceptions=False,
    )
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["entry_count"] == report.indexed_count
    assert payload["index_version"] == report.index_version
    assert payload["source"] == "local_metadata"
