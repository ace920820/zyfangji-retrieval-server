from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class SQLiteIndexStateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_exists = self.db_path.exists()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not db_exists:
            self._bootstrap_database()
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("pragma journal_mode=delete").fetchone()
        return connection

    def _bootstrap_database(self) -> None:
        with self.connect() as connection:
            connection.execute("create table if not exists __metadata_bootstrap (id integer)")

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                create table if not exists index_builds (
                    index_version text primary key,
                    metadata_version text not null,
                    status text not null,
                    entry_count integer not null,
                    vector_count integer not null,
                    bm25_doc_count integer not null,
                    provider_id text not null,
                    model_id text not null,
                    vector_size integer not null,
                    qdrant_collection text,
                    qdrant_alias text,
                    bm25_path text,
                    started_at text not null,
                    finished_at text,
                    updated_at text,
                    last_error text
                );

                create table if not exists active_index (
                    id integer primary key check (id = 1),
                    index_version text not null,
                    metadata_version text not null,
                    entry_count integer,
                    vector_count integer,
                    bm25_doc_count integer,
                    provider_id text,
                    model_id text,
                    vector_size integer,
                    qdrant_collection text not null,
                    qdrant_alias text not null,
                    bm25_path text not null,
                    activated_at text not null,
                    updated_at text not null
                );
                """
            )

    def start_build(self, record: IndexBuildRecord) -> IndexBuildRecord:
        now = _utc_now()
        started_at = record.started_at.isoformat(timespec="microseconds")
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    insert or replace into index_builds (
                        index_version,
                        metadata_version,
                        status,
                        entry_count,
                        vector_count,
                        bm25_doc_count,
                        provider_id,
                        model_id,
                        vector_size,
                        qdrant_collection,
                        qdrant_alias,
                        bm25_path,
                        started_at,
                        finished_at,
                        updated_at,
                        last_error
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.index_version,
                        record.metadata_version,
                        "building",
                        record.entry_count,
                        record.vector_count,
                        record.bm25_doc_count,
                        record.provider_id,
                        record.model_id,
                        record.vector_size,
                        record.qdrant_collection,
                        record.qdrant_alias,
                        record.bm25_path,
                        started_at,
                        None,
                        now,
                        None,
                    ),
                )
        loaded = self.get_build(record.index_version)
        if loaded is None:
            raise RuntimeError(f"failed to load started build: {record.index_version}")
        return loaded

    def mark_validated(
        self,
        index_version: str,
        vector_count: int,
        bm25_doc_count: int,
        qdrant_collection: str,
        bm25_path: str,
    ) -> IndexBuildRecord:
        now = _utc_now()
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    update index_builds
                    set status = ?,
                        vector_count = ?,
                        bm25_doc_count = ?,
                        qdrant_collection = ?,
                        bm25_path = ?,
                        finished_at = ?,
                        updated_at = ?,
                        last_error = null
                    where index_version = ?
                    """,
                    (
                        "validated",
                        vector_count,
                        bm25_doc_count,
                        qdrant_collection,
                        bm25_path,
                        now,
                        now,
                        index_version,
                    ),
                )
        return self._require_build(index_version)

    def mark_failed(self, index_version: str, error: str) -> IndexBuildRecord:
        now = _utc_now()
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    update index_builds
                    set status = ?,
                        finished_at = ?,
                        updated_at = ?,
                        last_error = ?
                    where index_version = ?
                    """,
                    ("failed", now, now, error, index_version),
                )
        return self._require_build(index_version)

    def activate(self, record: ActiveIndexRecord) -> ActiveIndexRecord:
        now = _utc_now()
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    insert or replace into active_index (
                        id,
                        index_version,
                        metadata_version,
                        entry_count,
                        vector_count,
                        bm25_doc_count,
                        provider_id,
                        model_id,
                        vector_size,
                        qdrant_collection,
                        qdrant_alias,
                        bm25_path,
                        activated_at,
                        updated_at
                    ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.index_version,
                        record.metadata_version,
                        record.entry_count,
                        record.vector_count,
                        record.bm25_doc_count,
                        record.provider_id,
                        record.model_id,
                        record.vector_size,
                        record.qdrant_collection,
                        record.qdrant_alias,
                        record.bm25_path,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    update index_builds
                    set status = ?,
                        qdrant_collection = ?,
                        qdrant_alias = ?,
                        bm25_path = ?,
                        updated_at = ?,
                        finished_at = coalesce(finished_at, ?),
                        last_error = null
                    where index_version = ?
                    """,
                    (
                        "active",
                        record.qdrant_collection,
                        record.qdrant_alias,
                        record.bm25_path,
                        now,
                        now,
                        record.index_version,
                    ),
                )
        active = self.get_active()
        if active is None:
            raise RuntimeError("failed to load active index")
        return active

    def get_active(self) -> ActiveIndexRecord | None:
        with self.connect() as connection:
            row = connection.execute("select * from active_index where id = 1").fetchone()
        if row is None:
            return None
        return self._active_from_row(row)

    def get_latest_build(self) -> IndexBuildRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                select * from index_builds
                order by updated_at desc, started_at desc, index_version desc
                limit 1
                """
            ).fetchone()
        if row is None:
            return None
        return self._build_from_row(row)

    def get_build(self, index_version: str) -> IndexBuildRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "select * from index_builds where index_version = ?",
                (index_version,),
            ).fetchone()
        if row is None:
            return None
        return self._build_from_row(row)

    def _require_build(self, index_version: str) -> IndexBuildRecord:
        record = self.get_build(index_version)
        if record is None:
            raise ValueError(f"index build does not exist: {index_version}")
        return record

    def _build_from_row(self, row: sqlite3.Row) -> IndexBuildRecord:
        return IndexBuildRecord(
            index_version=row["index_version"],
            metadata_version=row["metadata_version"],
            status=row["status"],
            entry_count=row["entry_count"],
            vector_count=row["vector_count"],
            bm25_doc_count=row["bm25_doc_count"],
            provider_id=row["provider_id"],
            model_id=row["model_id"],
            vector_size=row["vector_size"],
            qdrant_collection=row["qdrant_collection"],
            qdrant_alias=row["qdrant_alias"],
            bm25_path=row["bm25_path"],
            started_at=self._parse_datetime(row["started_at"]),
            finished_at=self._parse_optional_datetime(row["finished_at"]),
            updated_at=self._parse_optional_datetime(row["updated_at"]),
            last_error=row["last_error"],
        )

    def _active_from_row(self, row: sqlite3.Row) -> ActiveIndexRecord:
        return ActiveIndexRecord(
            index_version=row["index_version"],
            metadata_version=row["metadata_version"],
            qdrant_collection=row["qdrant_collection"],
            qdrant_alias=row["qdrant_alias"],
            bm25_path=row["bm25_path"],
            updated_at=self._parse_datetime(row["updated_at"]),
            entry_count=row["entry_count"],
            vector_count=row["vector_count"],
            bm25_doc_count=row["bm25_doc_count"],
            provider_id=row["provider_id"],
            model_id=row["model_id"],
            vector_size=row["vector_size"],
        )

    def _parse_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _parse_optional_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        return self._parse_datetime(str(value))
