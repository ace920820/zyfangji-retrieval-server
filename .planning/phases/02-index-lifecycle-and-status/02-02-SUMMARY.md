---
phase: 02-index-lifecycle-and-status
plan: 02
subsystem: indexing
tags: [bm25, jieba, sqlite, typer, qdrant, lifecycle, validation]
requires:
  - phase: 01-local-data-contract-and-ingestion
    provides: KnowledgeEntry rebuild source and load_entries_for_rebuild()
provides:
  - versioned BM25 local index persistence with Chinese tokenization
  - SQLite build-state and active-index truth records
  - validation-gated rebuild lifecycle and CLI rebuild/validate commands
affects: [03-hybrid-search-and-rerank-api, 04-quality-safety-and-performance-validation]
tech-stack:
  added: [bm25s==0.3.9, jieba==0.42.1]
  patterns: [versioned local BM25 artifacts, SQLite build ledger, validation-gated activation, CLI local rebuild workflow]
key-files:
  created:
    - src/zyfangji_retrieval/indexing/tokenizer.py
    - src/zyfangji_retrieval/indexing/tcm_terms.txt
    - src/zyfangji_retrieval/indexing/bm25_store.py
    - src/zyfangji_retrieval/persistence/index_state.py
    - src/zyfangji_retrieval/indexing/validation.py
    - src/zyfangji_retrieval/indexing/lifecycle.py
    - tests/test_bm25_indexing.py
    - tests/test_index_lifecycle.py
  modified:
    - src/zyfangji_retrieval/cli.py
    - src/zyfangji_retrieval/domain/index_models.py
    - src/zyfangji_retrieval/indexing/__init__.py
    - src/zyfangji_retrieval/indexing/bm25_store.py
    - src/zyfangji_retrieval/persistence/index_state.py
requirements-completed: [IDX-02, IDX-06, STAT-04]
duration: 9m24s
completed: 2026-06-14
---

# Phase 02 Plan 02: Index Lifecycle and Status Summary

**Versioned BM25 indexing, SQLite build state, and validation-gated rebuild activation for local TCM retrieval**

## Performance

- **Duration:** 9m 24s
- **Started:** 2026-06-14T15:02:06Z
- **Completed:** 2026-06-14T15:11:30Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments

- Added `jieba`-based Chinese tokenization with a bundled TCM dictionary and persisted BM25 indexes under versioned directories.
- Added SQLite `index_builds` and `active_index` tables so build attempts, failures, and the active index are recorded in one local truth source.
- Added rebuild orchestration that loads local metadata, validates vector/BM25 counts, and only activates after validation succeeds.
- Added `index-rebuild` and `index-validate` Typer commands that operate on local files and emit JSON.

## Task Commits

1. **Task 1: Build Chinese BM25 tokenizer and versioned local index store** - `f6ea819` (feat)
2. **Task 2: Persist index build records and active index state in SQLite** - `62c841e` (feat)
3. **Task 3: Orchestrate full rebuild, validation, activation, and CLI commands** - `436f369` (feat)

## Files Created/Modified

- `src/zyfangji_retrieval/indexing/tokenizer.py` - `jieba` tokenizer wrapper and bundled TCM dictionary loading.
- `src/zyfangji_retrieval/indexing/tcm_terms.txt` - Project term dictionary for exact TCM phrase retention.
- `src/zyfangji_retrieval/indexing/bm25_store.py` - Versioned BM25 build/save/load/validate store with metadata.
- `src/zyfangji_retrieval/persistence/index_state.py` - SQLite build ledger and singleton active-index table.
- `src/zyfangji_retrieval/indexing/validation.py` - Count/readiness helpers shared by lifecycle and CLI validation.
- `src/zyfangji_retrieval/indexing/lifecycle.py` - Full rebuild orchestration, validation gating, and failure recording.
- `src/zyfangji_retrieval/cli.py` - `index-rebuild` and `index-validate` commands.
- `src/zyfangji_retrieval/domain/index_models.py` - Added `activated_at` to active-index records.
- `tests/test_bm25_indexing.py` - BM25 tokenizer/store coverage.
- `tests/test_index_lifecycle.py` - Lifecycle, failure retention, and CLI coverage.

## Decisions Made

- Kept Phase 2 rebuild local-only and CLI-driven; no HTTP mutation endpoint was added.
- Used a bundled TCM term list instead of generic whitespace tokenization to preserve exact medical phrases.
- Treated SQLite as the unified active-index source; Qdrant alias activation mirrors state but does not replace it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Relaxed BM25 file validation to match actual `bm25s` outputs**
- **Found during:** Task 3 CLI verification
- **Issue:** Validation required optional files that `bm25s.BM25.save()` does not emit in this setup.
- **Fix:** Validated only the core persisted BM25 files plus `metadata.json`.
- **Files modified:** `src/zyfangji_retrieval/indexing/bm25_store.py`
- **Verification:** CLI rebuild/validate tests passed and BM25 reload tests still passed.
- **Committed in:** `436f369` (part of Task 3 commit)

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** No scope creep. The change aligned validation with the actual BM25 artifact set.

## Issues Encountered

- `bm25s` saved a smaller artifact set than first assumed, which surfaced during CLI validation. The validation logic was corrected and re-tested.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 can now build hybrid retrieval on top of versioned local BM25 artifacts and the validated index-state ledger without reworking the ingestion path.

## Self-Check: PASSED

- Created files exist: yes.
- Task commits found in history: `f6ea819`, `62c841e`, `436f369`.
- Verification passed: `pytest tests/test_bm25_indexing.py tests/test_index_lifecycle.py -q`, full regression suite, and `ruff check src tests`.

---
*Phase: 02-index-lifecycle-and-status*
*Completed: 2026-06-14*
