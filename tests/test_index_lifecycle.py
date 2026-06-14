import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore


def _build_record(index_version: str, status: str = "building") -> IndexBuildRecord:
    return IndexBuildRecord(
        index_version=index_version,
        metadata_version="local-v1",
        status=status,
        entry_count=2,
        vector_count=0,
        bm25_doc_count=0,
        provider_id="deterministic",
        model_id="deterministic-bge-m3-compatible",
        vector_size=4,
        started_at=datetime.now(UTC),
    )


def _active_record(index_version: str) -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version=index_version,
        metadata_version="local-v1",
        qdrant_collection=f"zyfangji_entries_{index_version}",
        qdrant_alias="zyfangji_entries_active",
        bm25_path=f"/tmp/bm25/{index_version}",
        updated_at=datetime.now(UTC),
        entry_count=2,
        vector_count=2,
        bm25_doc_count=2,
        provider_id="deterministic",
        model_id="deterministic-bge-m3-compatible",
        vector_size=4,
    )


def test_sqlite_index_state_store_creates_build_and_active_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    SQLiteIndexStateStore(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert {"index_builds", "active_index"} <= table_names


def test_sqlite_index_state_store_records_build_transitions(tmp_path: Path) -> None:
    store = SQLiteIndexStateStore(tmp_path / "metadata.db")
    build = _build_record("idx-20260614121000")

    started = store.start_build(build)
    validated = store.mark_validated(
        build.index_version,
        vector_count=2,
        bm25_doc_count=2,
        qdrant_collection="zyfangji_entries_idx_20260614121000",
        bm25_path="/tmp/bm25/idx-20260614121000",
    )
    failed = store.mark_failed(build.index_version, "provider timeout")

    assert started.status == "building"
    assert validated.status == "validated"
    assert validated.vector_count == 2
    assert validated.bm25_doc_count == 2
    assert failed.status == "failed"
    assert failed.last_error == "provider timeout"


def test_sqlite_index_state_store_activate_stores_single_active_row(tmp_path: Path) -> None:
    store = SQLiteIndexStateStore(tmp_path / "metadata.db")
    store.start_build(_build_record("idx-20260614121100"))
    active = _active_record("idx-20260614121100")

    stored = store.activate(active)

    assert stored == store.get_active()
    assert stored.index_version == "idx-20260614121100"
    assert stored.metadata_version == "local-v1"
    assert stored.qdrant_collection == "zyfangji_entries_idx-20260614121100"
    assert stored.qdrant_alias == "zyfangji_entries_active"
    assert stored.bm25_path == "/tmp/bm25/idx-20260614121100"
    assert stored.provider_id == "deterministic"
    assert stored.model_id == "deterministic-bge-m3-compatible"
    assert stored.vector_size == 4
    assert stored.entry_count == 2
    assert stored.vector_count == 2
    assert stored.bm25_doc_count == 2

    replacement = _active_record("idx-20260614121200")
    store.activate(replacement)
    with store.connect() as connection:
        active_rows = connection.execute("select count(*) from active_index").fetchone()[0]
    assert active_rows == 1
    assert store.get_active().index_version == "idx-20260614121200"


def test_failed_build_does_not_replace_previous_active_index(tmp_path: Path) -> None:
    """A failed build must not replace the previous active index."""
    store = SQLiteIndexStateStore(tmp_path / "metadata.db")
    store.start_build(_build_record("idx-20260614121300"))
    store.activate(_active_record("idx-20260614121300"))

    store.start_build(_build_record("idx-20260614121400"))
    failed = store.mark_failed("idx-20260614121400", "qdrant unavailable")

    active = store.get_active()
    assert failed.status == "failed"
    assert active is not None
    assert active.index_version == "idx-20260614121300"
