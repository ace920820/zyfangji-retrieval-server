---
phase: 02-index-lifecycle-and-status
reviewed: 2026-06-14T15:24:11Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/zyfangji_retrieval/config.py
  - src/zyfangji_retrieval/domain/index_models.py
  - src/zyfangji_retrieval/indexing/embeddings.py
  - src/zyfangji_retrieval/indexing/qdrant_store.py
  - src/zyfangji_retrieval/indexing/tokenizer.py
  - src/zyfangji_retrieval/indexing/bm25_store.py
  - src/zyfangji_retrieval/indexing/validation.py
  - src/zyfangji_retrieval/indexing/lifecycle.py
  - src/zyfangji_retrieval/indexing/status.py
  - src/zyfangji_retrieval/persistence/index_state.py
  - src/zyfangji_retrieval/cli.py
  - src/zyfangji_retrieval/api/app.py
  - src/zyfangji_retrieval/api/routes/status.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
resolved_findings:
  warning: 2
  commit: 1d76784
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-14T15:24:11Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** clean after fixes

## Summary

Reviewed the index lifecycle, BM25/vector state, persistence, CLI, and status API changes. The initial review found two lifecycle warnings; both were fixed in `1d76784`.

## Resolution

- WR-01 fixed: `QdrantVectorIndex.activate_alias()` now skips `DeleteAliasOperation` when the alias is missing and tests first-time activation plus replacement.
- WR-02 fixed: `build_index_version()` now uses microsecond precision and `SQLiteIndexStateStore.start_build()` uses plain `insert` so duplicate versions fail loudly.
- Verification after fixes: `pytest tests/test_qdrant_indexing.py tests/test_index_lifecycle.py -q` passed; `ruff check src tests` passed.

## Warnings

### WR-01: First Qdrant activation can fail when the alias does not exist

**File:** `src/zyfangji_retrieval/indexing/qdrant_store.py:120`

**Issue:** `activate_alias()` always submits a `DeleteAliasOperation` before creating the alias. On a fresh Qdrant instance, or after the alias has been manually removed, the alias does not exist yet. Qdrant commonly rejects deletion of a missing alias, so the first successful index build can fail during activation after both vector and BM25 validation have already passed.

**Fix:** Check existing aliases before deleting, or catch the specific "alias not found" response and continue. Prefer building the alias operation list conditionally, then create the alias.

```python
def activate_alias(self, index_version: str) -> str:
    collection_name = self.collection_name(index_version)
    operations = []
    if self._alias_exists(self.alias_name):
        operations.append(
            models.DeleteAliasOperation(
                delete_alias=models.DeleteAlias(alias_name=self.alias_name)
            )
        )
    operations.append(
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(
                collection_name=collection_name,
                alias_name=self.alias_name,
            )
        )
    )
    self.client.update_collection_aliases(change_aliases_operations=operations)
    return self.alias_name
```

### WR-02: Index version generation can collide within the same second

**File:** `src/zyfangji_retrieval/indexing/lifecycle.py:16`

**Issue:** `build_index_version()` uses second-level UTC timestamps. Two `index-rebuild` calls started in the same second produce the same `index_version`. Because `SQLiteIndexStateStore.start_build()` uses `insert or replace` for `index_builds`, the second build can overwrite the first build's state. Qdrant and BM25 also use this version in collection and directory names, so a collision can mix or replace artifacts across rebuilds.

**Fix:** Make build versions unique at microsecond precision or add a random/monotonic suffix, and avoid `insert or replace` for build records so accidental duplicates fail loudly.

```python
def build_index_version(prefix: str = "idx") -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}"
```

---

_Reviewed: 2026-06-14T15:24:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
