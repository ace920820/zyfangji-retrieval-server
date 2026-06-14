from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from zyfangji_retrieval.domain.ids import content_fingerprint
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import WorkbookRow
from zyfangji_retrieval.ingestion.reports import ImportReport, RowIssue


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class SQLiteMetadataStore:
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
            # Some external volumes reject a full schema script as the first write.
            connection.execute("create table if not exists __metadata_bootstrap (id integer)")

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                create table if not exists import_batches (
                    batch_id text primary key,
                    source_file text not null,
                    source_sheet text not null,
                    total_rows integer not null,
                    valid_rows integer not null,
                    skipped_rows integer not null,
                    warning_count integer not null,
                    indexed_count integer not null,
                    index_version text not null,
                    metadata_version text not null,
                    created_at text not null
                );

                create table if not exists raw_records (
                    batch_id text not null,
                    entry_id text,
                    source_row integer not null,
                    raw_json text not null
                );

                create table if not exists knowledge_entries (
                    batch_id text not null,
                    entry_id text not null,
                    source_row integer not null,
                    normalized_json text not null,
                    retrieval_text text not null,
                    formula_raw text not null,
                    formula_mapping_status text not null,
                    content_fingerprint text not null,
                    created_at text not null,
                    updated_at text not null,
                    primary key (batch_id, entry_id)
                );

                create table if not exists row_issues (
                    batch_id text not null,
                    source_row integer not null,
                    code text not null,
                    severity text not null,
                    message text not null
                );
                """
            )
            self._migrate_legacy_knowledge_entries(connection)

    def _migrate_legacy_knowledge_entries(self, connection: sqlite3.Connection) -> None:
        columns = connection.execute("pragma table_info(knowledge_entries)").fetchall()
        primary_key_columns = {
            column["name"]: column["pk"] for column in columns if column["pk"] > 0
        }
        if primary_key_columns != {"batch_id": 1, "entry_id": 2}:
            connection.executescript(
                """
                alter table knowledge_entries rename to knowledge_entries_legacy;

                create table knowledge_entries (
                    batch_id text not null,
                    entry_id text not null,
                    source_row integer not null,
                    normalized_json text not null,
                    retrieval_text text not null,
                    formula_raw text not null,
                    formula_mapping_status text not null,
                    content_fingerprint text not null,
                    created_at text not null,
                    updated_at text not null,
                    primary key (batch_id, entry_id)
                );

                insert or replace into knowledge_entries (
                    batch_id,
                    entry_id,
                    source_row,
                    normalized_json,
                    retrieval_text,
                    formula_raw,
                    formula_mapping_status,
                    content_fingerprint,
                    created_at,
                    updated_at
                )
                select
                    batch_id,
                    entry_id,
                    source_row,
                    normalized_json,
                    retrieval_text,
                    formula_raw,
                    formula_mapping_status,
                    content_fingerprint,
                    created_at,
                    updated_at
                from knowledge_entries_legacy;

                drop table knowledge_entries_legacy;
                """
            )

    def _entry_fingerprint(self, entry: KnowledgeEntry) -> str:
        return content_fingerprint(
            [
                entry.model_dump_json(),
                entry.retrieval_text,
                entry.formula_raw,
                entry.formula_mapping_status,
            ]
        )

    def save_import(
        self,
        batch_id: str,
        report: ImportReport,
        entries: Sequence[KnowledgeEntry],
        raw_rows: Sequence[WorkbookRow],
        issues: Sequence[RowIssue],
    ) -> None:
        entry_ids_by_row = {entry.source_row: entry.entry_id for entry in entries}
        now = _utc_now()
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    insert or replace into import_batches (
                        batch_id,
                        source_file,
                        source_sheet,
                        total_rows,
                        valid_rows,
                        skipped_rows,
                        warning_count,
                        indexed_count,
                        index_version,
                        metadata_version,
                        created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        report.source_file,
                        report.source_sheet,
                        report.total_rows,
                        report.valid_rows,
                        report.skipped_rows,
                        report.warning_count,
                        report.indexed_count,
                        report.index_version,
                        report.metadata_version,
                        now,
                    ),
                )
                connection.executemany(
                    """
                    insert into raw_records (
                        batch_id,
                        entry_id,
                        source_row,
                        raw_json
                    ) values (?, ?, ?, ?)
                    """,
                    [
                        (
                            batch_id,
                            entry_ids_by_row.get(row.source_row),
                            row.source_row,
                            _json_dump(row.raw_record),
                        )
                        for row in raw_rows
                    ],
                )
                connection.executemany(
                    """
                    insert or replace into knowledge_entries (
                        batch_id,
                        entry_id,
                        source_row,
                        normalized_json,
                        retrieval_text,
                        formula_raw,
                        formula_mapping_status,
                        content_fingerprint,
                        created_at,
                        updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            batch_id,
                            entry.entry_id,
                            entry.source_row,
                            entry.model_dump_json(),
                            entry.retrieval_text,
                            entry.formula_raw,
                            entry.formula_mapping_status,
                            self._entry_fingerprint(entry),
                            now,
                            now,
                        )
                        for entry in entries
                    ],
                )
                connection.executemany(
                    """
                    insert into row_issues (
                        batch_id,
                        source_row,
                        code,
                        severity,
                        message
                    ) values (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            batch_id,
                            issue.source_row,
                            issue.code,
                            issue.severity,
                            issue.message,
                        )
                        for issue in issues
                    ],
                )

    def load_entry(self, entry_id: str) -> KnowledgeEntry | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                select ke.normalized_json
                from knowledge_entries ke
                join import_batches ib on ib.batch_id = ke.batch_id
                where ke.entry_id = ?
                order by ib.created_at desc, ke.batch_id desc
                limit 1
                """,
                (entry_id,),
            ).fetchone()
        if row is None:
            return None
        return KnowledgeEntry.model_validate_json(row["normalized_json"])

    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        query = "select ke.normalized_json from knowledge_entries ke"
        params: tuple[str, ...] = ()
        if index_version is not None:
            query += """
                where ke.batch_id in (
                    select batch_id from import_batches where index_version = ?
                )
            """
            params = (index_version,)
        else:
            query += """
                join import_batches ib on ib.batch_id = ke.batch_id
                where not exists (
                    select 1
                    from knowledge_entries newer_ke
                    join import_batches newer_ib on newer_ib.batch_id = newer_ke.batch_id
                    where newer_ke.entry_id = ke.entry_id
                      and (
                          newer_ib.created_at > ib.created_at
                          or (
                              newer_ib.created_at = ib.created_at
                              and newer_ke.batch_id > ke.batch_id
                          )
                      )
                )
            """
        query += " order by source_row, entry_id"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [KnowledgeEntry.model_validate_json(row["normalized_json"]) for row in rows]

    def latest_batch(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "select * from import_batches order by created_at desc limit 1"
            ).fetchone()
        if row is None:
            return None
        return dict(row)
