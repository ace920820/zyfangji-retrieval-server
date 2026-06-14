---
phase: 01-local-data-contract-and-ingestion
plan: 03
subsystem: local-metadata-persistence
tags: [python, sqlite, jsonl, typer, ingestion, local-metadata]
requires: [01-01, 01-02]
provides:
  - SQLite metadata store for import batches, raw source rows, normalized entries, and row issues
  - End-to-end workbook import into local metadata without customer database access
  - Rebuild-source loading from SQLite metadata for later Qdrant/BM25 index phases
  - UTF-8 JSONL audit export and reload for KnowledgeEntry snapshots
  - Persistent CLI import and local rebuild-source inspection commands
affects: [phase-02-index-lifecycle, phase-03-search-api, local-operator-cli]
tech-stack:
  added: []
  patterns: [stdlib sqlite3 persistence, compact UTF-8 JSON serialization, Typer CLI persistence path, TDD persistence tests]
key-files:
  created:
    - src/zyfangji_retrieval/persistence/__init__.py
    - src/zyfangji_retrieval/persistence/sqlite.py
    - src/zyfangji_retrieval/persistence/jsonl.py
    - src/zyfangji_retrieval/ingestion/importer.py
    - tests/test_local_persistence.py
  modified:
    - src/zyfangji_retrieval/cli.py
key-decisions:
  - "Use SQLite as the authoritative local rebuild source for Phase 2 indexes, with JSONL as an audit/debug export format."
  - "Default import-excel to persistent import so the documented --db-path command creates local metadata; keep explicit --dry-run for report-only inspection."
  - "Keep CLI output to report/count JSON only; raw row text is stored in SQLite/JSONL, not printed to terminal logs."
requirements-completed: [ING-04, ING-05]
duration: 14min
completed: 2026-06-14
---

# Phase 01 Plan 03: Local Metadata Persistence Summary

**SQLite-backed local metadata with JSONL audit export and rebuildable workbook imports**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-14T08:07:27Z
- **Completed:** 2026-06-14T08:21:38Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `SQLiteMetadataStore` with the required `import_batches`, `raw_records`, `knowledge_entries`, and `row_issues` tables.
- Persisted import batches, raw workbook rows, normalized `KnowledgeEntry` JSON, retrieval text, formula mapping status, and row issues in one transaction.
- Added `import_workbook_to_metadata()` and `load_entries_for_rebuild()` so later indexing phases can rebuild from local metadata without customer MySQL.
- Added UTF-8 JSONL export/load helpers for one-JSON-object-per-line audit snapshots.
- Updated the CLI:
  - `import-excel --db-path ...` now persists by default.
  - `import-excel --dry-run` preserves report-only behavior.
  - `import-excel --jsonl-export ...` writes normalized entries after import.
  - `rebuild-source --db-path ...` prints local metadata counts and active index version.

## Task Commits

1. **Task 1 RED: SQLite metadata tests** - `1c5c96f` (`test`)
2. **Task 1 GREEN: SQLite metadata store** - `28469b2` (`feat`)
3. **Task 2 RED: persistent import tests** - `6cf8da8` (`test`)
4. **Task 2 GREEN: workbook import and rebuild loading** - `42030d3` (`feat`)
5. **Task 3 RED: JSONL and CLI persistence tests** - `7877265` (`test`)
6. **Task 3 GREEN: JSONL export and persistent CLI** - `c230686` (`feat`)
7. **CLI verification fix: persistent default** - `85673d5` (`fix`)
8. **SQLite external-volume fix** - `0c04814` (`fix`)

## Files Created/Modified

- `src/zyfangji_retrieval/persistence/sqlite.py` - SQLite local metadata store, table schema, transaction save, entry loading, latest-batch lookup, and external-volume bootstrap.
- `src/zyfangji_retrieval/persistence/jsonl.py` - JSONL audit export/load helpers for `KnowledgeEntry`.
- `src/zyfangji_retrieval/persistence/__init__.py` - Persistence exports.
- `src/zyfangji_retrieval/ingestion/importer.py` - End-to-end workbook import into SQLite and rebuild-source loading.
- `src/zyfangji_retrieval/cli.py` - Persistent import options, JSONL export option, and `rebuild-source` command.
- `tests/test_local_persistence.py` - TDD coverage for SQLite, persistent import, JSONL, CLI, and no customer database dependency.

## Decisions Made

- `knowledge_entries.entry_id` remains unique across re-imports; re-importing the same workbook updates the existing normalized entry row while each import batch remains recorded.
- `raw_records` are append-only per batch and preserve all 22 source fields as compact UTF-8 JSON.
- `rebuild-source` loads from SQLite metadata only and does not parse the workbook.
- The CLI defaults to persistent import because the plan verification command uses `import-excel ... --db-path ...` without `--no-dry-run`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made documented CLI import command persistent by default**
- **Found during:** Plan-level CLI verification
- **Issue:** `import-excel "..." --db-path var/metadata/knowledge.db` still used the old dry-run default and returned `index_version: dry-run` without creating metadata.
- **Fix:** Changed the `--dry-run/--no-dry-run` default to persistent import while preserving explicit `--dry-run`.
- **Files modified:** `src/zyfangji_retrieval/cli.py`
- **Commit:** `85673d5`

**2. [Rule 3 - Blocking] Bootstrapped SQLite files on the external project volume**
- **Found during:** Plan-level CLI verification
- **Issue:** SQLite writes to a brand-new `var/metadata/knowledge.db` on the KINGSTON external volume failed with `attempt to write a readonly database`.
- **Fix:** Set `journal_mode=delete` and perform a small bootstrap write before running the full schema script for new database files.
- **Files modified:** `src/zyfangji_retrieval/persistence/sqlite.py`
- **Commit:** `0c04814`

---

**Total deviations:** 2 auto-fixed issues.
**Impact on plan:** No scope expansion; both fixes make the planned commands work on the target workspace and preserve the local-only metadata boundary.

## Verification

- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv sync` - passed
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q` - passed, 41 tests
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python -m zyfangji_retrieval.cli import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db` - passed
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python -m zyfangji_retrieval.cli rebuild-source --db-path var/metadata/knowledge.db` - passed, `entry_count: 1246`
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` - passed

## Import Result

- `total_rows`: 1331
- `valid_rows`: 1246
- `skipped_rows`: 85
- `warning_count`: 221
- `indexed_count`: 1246
- `metadata_version`: `local-v1`
- `index_version`: `local-20260614082111`

## Known Stubs

None. Stub scan only found test fixtures and optional empty values used for validation cases.

## Threat Flags

None. The new local SQLite/JSONL file writes and CLI path handling are the planned Phase 1 trust boundaries; no network endpoints, auth paths, customer database access, or remote file reads were introduced.

## User Setup Required

None. Generated `var/metadata/knowledge.db` was used only for verification and removed from the worktree.

## Next Phase Readiness

Phase 2 can load `KnowledgeEntry` records through `load_entries_for_rebuild()` and build Qdrant/BM25 indexes without reparsing the workbook or depending on customer MySQL.

## Self-Check: PASSED

- Created files exist: persistence package, importer module, and `tests/test_local_persistence.py`.
- Task commits found: `1c5c96f`, `28469b2`, `6cf8da8`, `42030d3`, `7877265`, `c230686`, `85673d5`, `0c04814`.
- Required verification commands passed with `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv`.
- Generated metadata and cache files were removed before final status.

---
*Phase: 01-local-data-contract-and-ingestion*
*Completed: 2026-06-14*
