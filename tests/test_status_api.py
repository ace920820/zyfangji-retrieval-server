import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from zyfangji_retrieval.cli import app
from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord
from zyfangji_retrieval.indexing.status import IndexStatusService
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore


runner = CliRunner()


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


def _settings(db_path: Path) -> AppSettings:
    return AppSettings(db_path=db_path)


def test_index_status_service_reports_not_ready_and_latest_failure(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "metadata.db"
    store = SQLiteIndexStateStore(db_path)
    store.start_build(_build_record("idx-failed"))
    store.mark_failed("idx-failed", "provider unavailable")

    status = IndexStatusService(store, _settings(db_path)).status()

    assert status.ready is False
    assert status.active_version is None
    assert status.indexed_count == 0
    assert status.last_error == "provider unavailable"
    assert status.reranker_enabled is False
    assert status.reranker_model_id is None
    assert status.reranker_status == "not_configured"


def test_index_status_service_reports_active_index_details(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    store = SQLiteIndexStateStore(db_path)
    build = store.start_build(_build_record("idx-ready"))
    store.mark_validated(
        build.index_version,
        vector_count=2,
        bm25_doc_count=2,
        qdrant_collection="zyfangji_entries_idx-ready",
        bm25_path="/tmp/bm25/idx-ready",
    )
    store.activate(_active_record("idx-ready"))

    status = IndexStatusService(store, _settings(db_path)).status()

    assert status.ready is True
    assert status.active_version == "idx-ready"
    assert status.indexed_count == 2
    assert status.provider_id == "deterministic"
    assert status.model_id == "deterministic-bge-m3-compatible"
    assert status.vector_size == 4
    assert status.vector_store == "qdrant"
    assert status.retrieval_strategy == "bm25+dense"
    assert status.reranker_enabled is False
    assert status.reranker_model_id is None
    assert status.reranker_status == "not_configured"
    assert status.last_build_time is not None
    assert status.updated_at is not None


def test_index_status_cli_outputs_json_for_ready_and_not_ready_states(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "metadata.db"
    store = SQLiteIndexStateStore(db_path)
    store.start_build(_build_record("idx-failed"))
    store.mark_failed("idx-failed", "provider unavailable")

    not_ready = runner.invoke(
        app,
        ["index-status", "--db-path", str(db_path)],
        catch_exceptions=False,
    )

    assert not_ready.exit_code == 0
    not_ready_payload = json.loads(not_ready.output)
    assert not_ready_payload["ready"] is False
    assert not_ready_payload["active_version"] is None
    assert not_ready_payload["indexed_count"] == 0
    assert not_ready_payload["last_error"] == "provider unavailable"
    assert not_ready_payload["reranker_enabled"] is False
    assert not_ready_payload["reranker_model_id"] is None
    assert not_ready_payload["reranker_status"] == "not_configured"

    store.start_build(_build_record("idx-ready"))
    store.mark_validated(
        "idx-ready",
        vector_count=2,
        bm25_doc_count=2,
        qdrant_collection="zyfangji_entries_idx-ready",
        bm25_path="/tmp/bm25/idx-ready",
    )
    store.activate(_active_record("idx-ready"))

    ready = runner.invoke(
        app,
        ["index-status", "--db-path", str(db_path)],
        catch_exceptions=False,
    )

    assert ready.exit_code == 0
    ready_payload = json.loads(ready.output)
    assert ready_payload["ready"] is True
    assert ready_payload["active_version"] == "idx-ready"
    assert ready_payload["indexed_count"] == 2
    assert ready_payload["provider_id"] == "deterministic"
    assert ready_payload["model_id"] == "deterministic-bge-m3-compatible"
    assert ready_payload["reranker_status"] == "not_configured"
