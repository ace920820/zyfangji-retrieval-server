---
phase: 01-local-data-contract-and-ingestion
reviewed: 2026-06-14T08:25:56Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - pyproject.toml
  - src/zyfangji_retrieval/domain/models.py
  - src/zyfangji_retrieval/domain/ids.py
  - src/zyfangji_retrieval/ingestion/retrieval_text.py
  - src/zyfangji_retrieval/ingestion/formulas.py
  - src/zyfangji_retrieval/ingestion/excel_reader.py
  - src/zyfangji_retrieval/ingestion/mapper.py
  - src/zyfangji_retrieval/ingestion/reports.py
  - src/zyfangji_retrieval/ingestion/importer.py
  - src/zyfangji_retrieval/persistence/sqlite.py
  - src/zyfangji_retrieval/persistence/jsonl.py
  - src/zyfangji_retrieval/cli.py
  - tests/test_domain_contracts.py
  - tests/test_excel_ingestion.py
  - tests/test_local_persistence.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: clean
---

# Phase 1: Code Review Report

**Reviewed:** 2026-06-14T08:25:56Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** clean after fix

## Summary

Reviewed the Phase 1 local data contract, Excel ingestion, mapper, report, SQLite/JSONL persistence, CLI, and focused tests. The implementation preserves the 22-column source record, keeps Excel `编码` separate from deterministic IDs, avoids customer MySQL dependencies, and does not print raw clinical-like row text in CLI output.

One correctness issue remains in SQLite versioned rebuild behavior: older import/index versions stop being rebuildable after re-importing the same entries.

**Resolution:** Fixed after review. `knowledge_entries` now stores versioned snapshots by `(batch_id, entry_id)`, default reads return the latest per-entry snapshot, specific `index_version` rebuilds query that batch directly, and a regression test covers importing the same workbook twice.

## Warnings

### WR-01: Previous Index Versions Cannot Be Rebuilt After Re-Import

**File:** `src/zyfangji_retrieval/persistence/sqlite.py:67`

**Issue:** `knowledge_entries` uses `entry_id` as the primary key and `save_import()` overwrites the row's `batch_id` on re-import (`insert or replace` at lines 159-180). `load_entries(index_version=...)` then filters by `batch_id` through `import_batches` at lines 217-224. After importing the same workbook twice, the first version's entries have been moved to the second batch, so `load_entries_for_rebuild(db, first_report.index_version)` returns `0` even though the first import batch still exists and originally indexed 1246 entries. This breaks the advertised rebuild/audit contract for a specific `index_version`.

**Fix:** Store versioned entry snapshots separately from the current-entry view, or make `knowledge_entries` versioned by `(batch_id, entry_id)` and query the requested batch directly. For example:

```python
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
```

Then load a requested version with:

```python
select normalized_json
from knowledge_entries
where batch_id in (
    select batch_id from import_batches where index_version = ?
)
order by source_row, entry_id
```

Add a regression test that imports the sample workbook twice and asserts both `load_entries_for_rebuild(db, first.index_version)` and `load_entries_for_rebuild(db, second.index_version)` return their respective `indexed_count`.

---

_Reviewed: 2026-06-14T08:25:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
