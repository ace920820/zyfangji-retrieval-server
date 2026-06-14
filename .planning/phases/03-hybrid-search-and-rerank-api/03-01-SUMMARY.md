---
phase: 03-hybrid-search-and-rerank-api
plan: 01
subsystem: api
tags: [fastapi, pydantic, search-contract, openapi, validation]
requires:
  - phase: 02-index-lifecycle-and-status
    provides: "Read-only FastAPI app/status foundation and BGE/Qdrant/BM25 configuration patterns"
provides:
  - "Bounded patient search request schema with Java-facing response, score, warning, and error contracts"
  - "Labeled patient query text construction for main symptom, symptom list, tongue, pulse, and syndrome"
  - "POST /api/search route contract with stable 422 and 503 error envelopes"
affects: [03-hybrid-search-and-rerank-api, 04-quality-safety-and-performance-validation, 05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["Pydantic v2 request/response contracts", "FastAPI app.state service injection", "Stable JSON error envelopes"]
key-files:
  created:
    - src/zyfangji_retrieval/domain/search_models.py
    - src/zyfangji_retrieval/search/__init__.py
    - src/zyfangji_retrieval/search/query.py
    - src/zyfangji_retrieval/api/routes/search.py
    - tests/test_search_contracts.py
  modified:
    - src/zyfangji_retrieval/config.py
    - src/zyfangji_retrieval/api/app.py
    - src/zyfangji_retrieval/api/routes/__init__.py
    - tests/test_status_api.py
key-decisions:
  - "Runtime embedding defaults now target BGE-M3; deterministic embedding remains available only through explicit settings override."
  - "Search route returns validation failures under detail.error to preserve stable Java-facing error paths."
  - "The route exposes only a stateless POST /api/search contract; retrieval orchestration remains in later Phase 3 plans."
patterns-established:
  - "Score semantics live in SearchResponse and explicitly reject medical confidence/probability/certainty interpretation."
  - "Patient query text mirrors ingestion retrieval_text labels and emits non-diagnostic query quality warnings."
requirements-completed: [PIPE-01, PIPE-02, PIPE-07, RES-03, RES-05]
duration: 7min
completed: 2026-06-14
---

# Phase 03 Plan 01: Search Contract and Route Summary

**Java-facing search API contract with bounded patient input, labeled query text, score semantics, and stable FastAPI error envelopes**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-14T16:38:55Z
- **Completed:** 2026-06-14T16:45:36Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added bounded `PatientSearchRequest` validation for presentation fields, symptom list size/item length, `topk=10` default, and `topk<=50`.
- Added response, result, score, evidence, warning, metadata, and error envelope schemas with explicit score-safety semantics.
- Added `build_patient_query()` to convert structured patient fields into labeled Chinese query text and warnings for sparse or broad queries.
- Registered `POST /api/search` with `response_model=SearchResponse`, service injection through `app.state.search_service`, and stable 422/503 JSON envelopes.

## Task Commits

1. **Task 1: Add search settings and Pydantic contracts** - `19d8162` (`feat`)
2. **Task 2: Build labeled patient query text and query warnings** - `f5c3904` (`feat`)
3. **Task 3: Register POST /api/search with stable error envelopes** - `04cda95` (`feat`)

## Files Created/Modified

- `src/zyfangji_retrieval/domain/search_models.py` - Patient search request/response/result/warning/score/evidence/error contracts.
- `src/zyfangji_retrieval/search/query.py` - Labeled patient query text builder and query-quality warning generation.
- `src/zyfangji_retrieval/search/__init__.py` - Search package exports.
- `src/zyfangji_retrieval/api/routes/search.py` - `POST /api/search` route, unavailable-service handling, and documented response models.
- `src/zyfangji_retrieval/api/app.py` - Search route registration and FastAPI validation-error handler.
- `src/zyfangji_retrieval/api/routes/__init__.py` - Route module exports.
- `src/zyfangji_retrieval/config.py` - BGE-M3 and BGE reranker defaults plus search/fusion settings.
- `tests/test_search_contracts.py` - Contract, query builder, and search route tests.
- `tests/test_status_api.py` - Existing route-surface assertion updated to allow the planned stateless search endpoint.

## Decisions Made

- Runtime defaults now use `embedding_provider="bge_m3"`, `embedding_model_id="BAAI/bge-m3"`, and `embedding_vector_size=1024`; deterministic mode remains a test/dev override rather than the default.
- Validation errors are returned at `detail.error.*` because FastAPI validation failures conventionally live under `detail`, and the plan required Java clients to read `detail.error.code`.
- This plan stops at the route contract and fake-service dispatch; BM25/vector/fusion/rerank orchestration remains for subsequent Phase 3 plans.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved validation precedence for invalid request bodies**
- **Found during:** Task 3
- **Issue:** An initial dependency shape checked `app.state.search_service` before body validation, causing `topk: 51` to return 503 instead of the planned stable 422 validation envelope.
- **Fix:** Moved service lookup into the route after `PatientSearchRequest` validation so invalid bodies reliably return `detail.error.code == "validation_error"`.
- **Files modified:** `src/zyfangji_retrieval/api/routes/search.py`
- **Verification:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_contracts.py tests/test_status_api.py -q`
- **Committed in:** `04cda95`

**2. [Rule 1 - Bug] Updated stale route-surface test for the new planned endpoint**
- **Found during:** Task 3
- **Issue:** The Phase 2 status-route test intentionally rejected any search path, which conflicted with this plan's required `POST /api/search` route.
- **Fix:** Updated the assertion to keep status routes read-only while allowing exactly the stateless `POST /api/search` endpoint and continuing to reject import/rebuild/hybrid/rerank mutation endpoints.
- **Files modified:** `tests/test_status_api.py`
- **Verification:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_contracts.py tests/test_status_api.py -q`
- **Committed in:** `04cda95`

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both fixes were required for the planned API contract and did not add extra product scope.

## Issues Encountered

- FastAPI treats multiple body model parameters across route/dependency as a composed body object. The implementation was adjusted to keep a single request body model and preserve normal validation behavior.

## Known Stubs

None. Nullable response/config fields are intentional contract defaults for future provider and evidence population.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: network_endpoint | `src/zyfangji_retrieval/api/routes/search.py` | Adds the planned Java-facing `POST /api/search` trust boundary. Mitigations are bounded Pydantic input, no request-body logging, stable error envelopes, and score-safety semantics. |

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_contracts.py tests/test_status_api.py -q` -> 28 passed, 1 deprecation warning from FastAPI TestClient import path.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` -> All checks passed.

## User Setup Required

None - no external service configuration required for this contract-only plan.

## Next Phase Readiness

The route can now dispatch to any object assigned to `app.state.search_service` with `search(request: PatientSearchRequest) -> SearchResponse`. Plan 03-02 can implement the BM25/vector/fusion/rerank service behind this contract.

## Self-Check: PASSED

- Found summary and key implementation files.
- Found task commits `19d8162`, `f5c3904`, and `04cda95` in git history.

---
*Phase: 03-hybrid-search-and-rerank-api*
*Completed: 2026-06-14*
