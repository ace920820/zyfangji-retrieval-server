---
phase: 02-index-lifecycle-and-status
plan: 03
subsystem: api
tags: [fastapi, health-checks, readiness, status, typer, sqlite]
requires:
  - phase: 02-index-lifecycle-and-status
    plan: 02
    provides: SQLite active index and latest build records
provides:
  - read-only FastAPI liveness, readiness, and status endpoints
  - CLI index-status JSON output
  - IndexStatusService backed by SQLite active/latest build state
affects: [03-hybrid-search-and-rerank-api, 05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: [shared CLI/API status service, readiness from active index consistency, explicit Phase 2 reranker not_configured fields]
key-files:
  created:
    - src/zyfangji_retrieval/indexing/status.py
    - src/zyfangji_retrieval/api/__init__.py
    - src/zyfangji_retrieval/api/app.py
    - src/zyfangji_retrieval/api/routes/__init__.py
    - src/zyfangji_retrieval/api/routes/status.py
    - tests/test_status_api.py
  modified:
    - src/zyfangji_retrieval/cli.py
    - src/zyfangji_retrieval/domain/index_models.py
    - tests/test_status_api.py
key-decisions:
  - "Readiness is derived only from SQLite active state plus count consistency; no embedding, Qdrant, or reranker calls run in status handlers."
  - "Phase 2 reports reranker fields explicitly as not_configured because reranker execution and configuration are Phase 3 scope."
  - "HTTP surface remains read-only: liveness, readiness, and status only."
requirements-completed: [IDX-03, STAT-01, STAT-02, STAT-03]
duration: 5m24s
completed: 2026-06-14
---

# Phase 02 Plan 03: Status API and Health Summary

**Read-only FastAPI and CLI status surfaces backed by SQLite active-index truth**

## Performance

- **Duration:** 5m 24s
- **Started:** 2026-06-14T15:13:40Z
- **Completed:** 2026-06-14T15:19:04Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added `IndexStatusService` that builds status JSON from `SQLiteIndexStateStore.get_active()` and `get_latest_build()`.
- Added `index-status --db-path ...` CLI output with readiness, active version, indexed count, provider/model identifiers, timestamps, last error, and explicit reranker `not_configured` fields.
- Added FastAPI `create_app()` plus `GET /health/live`, `GET /health/ready`, and `GET /status`.
- Added readiness behavior where no active index or inconsistent active counts returns 503, while `/status` still returns 200 with `ready=false`.
- Added route-surface tests proving Phase 2 does not add search, rebuild/import mutation, hybrid, or reranker endpoints.

## Task Commits

1. **Task 1: Build IndexStatus service and CLI status output** - `25f8ec5` (feat)
2. **Task 2: Expose FastAPI status and health/readiness endpoints** - `a43f627` (feat)

## Files Created/Modified

- `src/zyfangji_retrieval/indexing/status.py` - Shared service for CLI/API status from SQLite state.
- `src/zyfangji_retrieval/cli.py` - Added `index-status`.
- `src/zyfangji_retrieval/domain/index_models.py` - Added status contract fields expected by operators and HTTP callers.
- `src/zyfangji_retrieval/api/__init__.py` - Exported app factory.
- `src/zyfangji_retrieval/api/app.py` - Added FastAPI app factory and module app.
- `src/zyfangji_retrieval/api/routes/__init__.py` - Exported status router.
- `src/zyfangji_retrieval/api/routes/status.py` - Added liveness, readiness, and status routes.
- `tests/test_status_api.py` - Covered ready, not-ready, failure visibility, CLI output, HTTP status, and route-surface constraints.

## Decisions Made

- Status/readiness do not call embedding providers, Qdrant network APIs, BM25 loaders, or rerankers.
- Readiness requires an active index with `entry_count > 0`, matching vector and BM25 counts, and a non-empty BM25 path.
- `last_error` is surfaced from the latest failed build when present, including when an older active index still exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Serialized readiness failure detail in JSON mode**
- **Found during:** Task 2 API verification
- **Issue:** `HTTPException(detail=status.model_dump())` included `datetime` objects that Starlette could not JSON-serialize on 503 responses.
- **Fix:** Changed readiness failure detail to `status.model_dump(mode="json")`.
- **Files modified:** `src/zyfangji_retrieval/api/routes/status.py`
- **Verification:** `tests/test_status_api.py` and the full regression suite passed.
- **Committed in:** `a43f627`

## Issues Encountered

- `fastapi.testclient` emits a dependency deprecation warning from FastAPI/Starlette about `httpx`; tests pass and no project code is affected.

## Known Stubs

None. Stub scan found only schema defaults and ordinary local list accumulators.

## Authentication Gates

None.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_status_api.py -q` - passed, 9 tests
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py -q` - passed, 78 tests
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` - passed
- Acceptance greps for status service, CLI command, read-only routes, reranker fields, and absence of provider/reranker/search/mutation calls - passed

## Next Phase Readiness

Phase 3 can add patient retrieval endpoints against this health/status foundation without changing the Phase 2 readiness contract.

## Self-Check: PASSED

- Created files verified on disk.
- Task commits verified in git history: `25f8ec5`, `a43f627`.

---
*Phase: 02-index-lifecycle-and-status*
*Completed: 2026-06-14*
