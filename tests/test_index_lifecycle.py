import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from zyfangji_retrieval import cli as cli_module
from zyfangji_retrieval.cli import app
from zyfangji_retrieval.domain.index_models import IndexValidationResult
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.ingestion.importer import import_workbook_to_metadata
from zyfangji_retrieval.indexing.lifecycle import (
    IndexLifecycleError,
    IndexLifecycleService,
    build_index_version,
)
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore


runner = CliRunner()
SAMPLE_WORKBOOK = Path("data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx")


class FakeEmbeddingProvider:
    provider_id = "fake-provider"
    model_id = "fake-model"
    vector_size = 4

    def __init__(self, fail: bool = False, vectors: list[list[float]] | None = None) -> None:
        self.fail = fail
        self.vectors = vectors
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts = list(texts)
        if self.fail:
            raise RuntimeError("provider unavailable")
        if self.vectors is not None:
            return self.vectors
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class FakeQdrantIndex:
    def __init__(self, fail_on: str | None = None, validation_valid: bool = True) -> None:
        self.fail_on = fail_on
        self.validation_valid = validation_valid
        self.calls: list[str] = []

    def create_collection(self, index_version: str) -> str:
        self.calls.append("create_collection")
        if self.fail_on == "create_collection":
            raise RuntimeError("qdrant create failed")
        return f"zyfangji_entries_{index_version}"

    def upsert_entries(
        self,
        index_version: str,
        entries: list[KnowledgeEntry],
        vectors: list[list[float]],
    ) -> int:
        self.calls.append("upsert_entries")
        if self.fail_on == "upsert_entries":
            raise RuntimeError("qdrant upsert failed")
        return len(entries)

    def validate_collection(self, index_version: str, expected_count: int) -> IndexValidationResult:
        self.calls.append("validate_collection")
        if self.fail_on == "validate_collection":
            raise RuntimeError("qdrant validation failed")
        return IndexValidationResult(
            index_version=index_version,
            valid=self.validation_valid,
            expected_count=expected_count,
            vector_count=expected_count if self.validation_valid else expected_count - 1,
            bm25_doc_count=0,
            errors=[] if self.validation_valid else ["vector count mismatch"],
            qdrant_collection=f"zyfangji_entries_{index_version}",
            qdrant_alias="zyfangji_entries_active",
        )

    def activate_alias(self, index_version: str) -> str:
        self.calls.append("activate_alias")
        if self.fail_on == "activate_alias":
            raise RuntimeError("alias failed")
        return "zyfangji_entries_active"


class FakeBM25Store:
    def __init__(self, fail_build: bool = False, valid: bool = True) -> None:
        self.fail_build = fail_build
        self.valid = valid
        self.calls: list[str] = []

    def build(self, index_version: str, entries: list[KnowledgeEntry]) -> Any:
        self.calls.append("build")
        if self.fail_build:
            raise RuntimeError("bm25 build failed")
        return type(
            "Metadata",
            (),
            {
                "doc_count": len(entries),
                "entry_ids": [entry.entry_id for entry in entries],
            },
        )()

    def validate(self, index_version: str, expected_count: int) -> IndexValidationResult:
        self.calls.append("validate")
        return IndexValidationResult(
            index_version=index_version,
            valid=self.valid,
            expected_count=expected_count,
            vector_count=0,
            bm25_doc_count=expected_count if self.valid else expected_count - 1,
            errors=[] if self.valid else ["bm25 doc count mismatch"],
            bm25_path=f"/tmp/bm25/{index_version}",
        )


def _entry_fixture(entry_id: str = "entry-1") -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_sheet="伤寒论",
        source_row=1,
        formula_raw="麻黄汤",
        formula_mentions=[FormulaMention(name="麻黄汤")],
        formula_mapping_status="parsed",
        retrieval_text="主症:\n太阳病 恶风\n\n脉象:\n脉浮紧",
        raw_record={},
        normalized_record={},
    )


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


def test_build_index_version_uses_microsecond_precision() -> None:
    index_version = build_index_version()

    assert index_version.startswith("idx-")
    assert len(index_version.removeprefix("idx-")) == 20


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


def test_sqlite_index_state_store_rejects_duplicate_build_versions(tmp_path: Path) -> None:
    store = SQLiteIndexStateStore(tmp_path / "metadata.db")
    build = _build_record("idx-20260614121000123456")

    store.start_build(build)

    with pytest.raises(sqlite3.IntegrityError):
        store.start_build(build)


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


def test_lifecycle_rebuild_loads_entries_from_local_metadata_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_args: dict[str, object] = {}

    def fake_load_entries_for_rebuild(
        db_path: Path,
        index_version: str | None = None,
    ) -> list[KnowledgeEntry]:
        loaded_args["db_path"] = db_path
        loaded_args["index_version"] = index_version
        return [_entry_fixture()]

    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.load_entries_for_rebuild",
        fake_load_entries_for_rebuild,
    )
    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.build_index_version",
        lambda: "idx-20260614121500",
    )
    store = SQLiteIndexStateStore(tmp_path / "metadata.db")
    service = IndexLifecycleService(
        db_path=tmp_path / "metadata.db",
        metadata_version="local-v1",
        embedding_provider=FakeEmbeddingProvider(),
        qdrant_index=FakeQdrantIndex(),
        bm25_store=FakeBM25Store(),
        index_state_store=store,
    )

    record = service.rebuild(activate=False)

    assert loaded_args == {"db_path": tmp_path / "metadata.db", "index_version": "local-v1"}
    assert record.status == "validated"


def test_lifecycle_successful_rebuild_validates_then_activates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.load_entries_for_rebuild",
        lambda db_path, index_version=None: [_entry_fixture(), _entry_fixture("entry-2")],
    )
    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.build_index_version",
        lambda: "idx-20260614121600",
    )
    provider = FakeEmbeddingProvider()
    qdrant = FakeQdrantIndex()
    bm25 = FakeBM25Store()
    state = SQLiteIndexStateStore(tmp_path / "metadata.db")
    service = IndexLifecycleService(
        db_path=tmp_path / "metadata.db",
        metadata_version="local-v1",
        embedding_provider=provider,
        qdrant_index=qdrant,
        bm25_store=bm25,
        index_state_store=state,
    )

    record = service.rebuild(activate=True)
    active = state.get_active()

    assert provider.texts == [
        "主症:\n太阳病 恶风\n\n脉象:\n脉浮紧",
        "主症:\n太阳病 恶风\n\n脉象:\n脉浮紧",
    ]
    assert qdrant.calls == [
        "create_collection",
        "upsert_entries",
        "validate_collection",
        "activate_alias",
    ]
    assert bm25.calls == ["build", "validate"]
    assert record.status == "active"
    assert record.entry_count == 2
    assert record.vector_count == 2
    assert record.bm25_doc_count == 2
    assert active is not None
    assert active.index_version == "idx-20260614121600"
    assert active.entry_count == 2


@pytest.mark.parametrize(
    ("provider", "qdrant", "bm25", "expected_error"),
    [
        (FakeEmbeddingProvider(fail=True), FakeQdrantIndex(), FakeBM25Store(), "provider unavailable"),
        (FakeEmbeddingProvider(), FakeQdrantIndex(fail_on="upsert_entries"), FakeBM25Store(), "qdrant upsert failed"),
        (FakeEmbeddingProvider(), FakeQdrantIndex(), FakeBM25Store(fail_build=True), "bm25 build failed"),
        (FakeEmbeddingProvider(), FakeQdrantIndex(validation_valid=False), FakeBM25Store(), "vector count mismatch"),
        (FakeEmbeddingProvider(), FakeQdrantIndex(), FakeBM25Store(valid=False), "bm25 doc count mismatch"),
    ],
)
def test_lifecycle_failures_mark_failed_and_keep_previous_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: FakeEmbeddingProvider,
    qdrant: FakeQdrantIndex,
    bm25: FakeBM25Store,
    expected_error: str,
) -> None:
    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.load_entries_for_rebuild",
        lambda db_path, index_version=None: [_entry_fixture()],
    )
    versions = iter(["idx-20260614121700"])
    monkeypatch.setattr(
        "zyfangji_retrieval.indexing.lifecycle.build_index_version",
        lambda: next(versions),
    )
    state = SQLiteIndexStateStore(tmp_path / "metadata.db")
    state.start_build(_build_record("idx-previous"))
    state.activate(_active_record("idx-previous"))
    service = IndexLifecycleService(
        db_path=tmp_path / "metadata.db",
        metadata_version="local-v1",
        embedding_provider=provider,
        qdrant_index=qdrant,
        bm25_store=bm25,
        index_state_store=state,
    )

    with pytest.raises(IndexLifecycleError, match=expected_error):
        service.rebuild(activate=True)

    failed = state.get_build("idx-20260614121700")
    active = state.get_active()
    assert failed is not None
    assert failed.status == "failed"
    assert expected_error in (failed.last_error or "")
    assert active is not None
    assert active.index_version == "idx-previous"


def test_index_rebuild_cli_no_activate_validates_without_setting_active(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    bm25_root = tmp_path / "bm25"
    import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)

    result = runner.invoke(
        app,
        [
            "index-rebuild",
            "--db-path",
            str(db_path),
            "--bm25-index-root",
            str(bm25_root),
            "--local-demo",
            "--no-activate",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert '"status": "validated"' in result.output
    assert SQLiteIndexStateStore(db_path).get_active() is None


def test_index_rebuild_cli_activate_sets_active_index(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    bm25_root = tmp_path / "bm25"
    import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)

    result = runner.invoke(
        app,
        [
            "index-rebuild",
            "--db-path",
            str(db_path),
            "--bm25-index-root",
            str(bm25_root),
            "--local-demo",
            "--activate",
        ],
        catch_exceptions=False,
    )

    active = SQLiteIndexStateStore(db_path).get_active()
    assert result.exit_code == 0
    assert '"status": "active"' in result.output
    assert active is not None
    assert active.index_version in result.output


def test_index_rebuild_cli_uses_configured_embedding_provider_and_qdrant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "metadata.db"
    bm25_root = tmp_path / "bm25"
    import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)
    calls: dict[str, object] = {}

    class ConfiguredProvider(FakeEmbeddingProvider):
        provider_id = "silicon"
        model_id = "BAAI/bge-m3"
        vector_size = 4

    class ConfiguredQdrantIndex(FakeQdrantIndex):
        def __init__(
            self,
            client: object,
            collection_prefix: str,
            alias_name: str,
            vector_size: int,
        ) -> None:
            super().__init__()
            calls["qdrant_client"] = client
            calls["collection_prefix"] = collection_prefix
            calls["alias_name"] = alias_name
            calls["vector_size"] = vector_size

        def create_collection(self, index_version: str) -> str:
            self.calls.append("create_collection")
            return f"configured_{index_version}"

    class ConfiguredQdrantClient:
        def __init__(self, *, url: str) -> None:
            self.url = url
            calls["qdrant_url"] = url

    monkeypatch.setenv("ZYFANGJI_EMBEDDING_PROVIDER", "silicon")
    monkeypatch.setenv("ZYFANGJI_EMBEDDING_ENDPOINT_URL", "https://example.test/embeddings")
    monkeypatch.setenv("ZYFANGJI_EMBEDDING_API_KEY", "secret-key")
    monkeypatch.setenv("ZYFANGJI_EMBEDDING_VECTOR_SIZE", "4")
    monkeypatch.setenv("ZYFANGJI_QDRANT_URL", "http://localhost:6333")
    monkeypatch.setattr(cli_module, "build_embedding_provider", lambda settings: ConfiguredProvider())
    monkeypatch.setattr(cli_module, "QdrantVectorIndex", ConfiguredQdrantIndex)
    monkeypatch.setattr(cli_module, "QdrantClient", ConfiguredQdrantClient)

    result = runner.invoke(
        app,
        [
            "index-rebuild",
            "--db-path",
            str(db_path),
            "--bm25-index-root",
            str(bm25_root),
            "--no-activate",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert '"provider_id": "silicon"' in result.output
    assert '"model_id": "BAAI/bge-m3"' in result.output
    assert calls["qdrant_url"] == "http://localhost:6333"
    assert calls["collection_prefix"] == "zyfangji_entries"
    assert calls["alias_name"] == "zyfangji_entries_active"
    assert calls["vector_size"] == 4


def test_index_validate_cli_returns_validation_without_mutating_active(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    bm25_root = tmp_path / "bm25"
    import_workbook_to_metadata(SAMPLE_WORKBOOK, db_path)
    rebuild_result = runner.invoke(
        app,
        [
            "index-rebuild",
            "--db-path",
            str(db_path),
            "--bm25-index-root",
            str(bm25_root),
            "--local-demo",
            "--no-activate",
        ],
        catch_exceptions=False,
    )
    payload = rebuild_result.output
    index_version = payload.split('"index_version": "')[1].split('"', maxsplit=1)[0]

    result = runner.invoke(
        app,
        [
            "index-validate",
            "--db-path",
            str(db_path),
            "--bm25-index-root",
            str(bm25_root),
            "--index-version",
            index_version,
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert '"valid": true' in result.output
    assert '"bm25_doc_count": 1246' in result.output
    assert SQLiteIndexStateStore(db_path).get_active() is None
