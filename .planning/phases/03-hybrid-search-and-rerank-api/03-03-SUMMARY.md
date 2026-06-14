---
phase: 03-hybrid-search-and-rerank-api
plan: 03
subsystem: api
tags: [fastapi, search-contract, evidence-projection, bge-m3, qdrant, rerank]
requires:
  - phase: 03-hybrid-search-and-rerank-api
    plan: 01
    provides: "Search request/response contracts and POST /api/search route"
  - phase: 03-hybrid-search-and-rerank-api
    plan: 02
    provides: "BM25/vector fusion and reranker SearchService orchestration"
provides:
  - "Java-friendly search response with formula identity, source metadata, evidence fields, signal scores, and score semantics"
  - "FastAPI app wiring for active SearchService with lazy BGE-M3 embedding provider construction"
  - "Stable error envelopes for validation, index, embedding provider, reranker, and unexpected search failures"
  - "Endpoint contract tests for TopK bounds, warnings, score semantics, and non-search health/status behavior"
affects: [04-quality-safety-and-performance-validation, 05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["Evidence projector module", "Lazy provider factory for search-time embedding construction", "Java-facing stable error envelope mapping"]
key-files:
  created:
    - src/zyfangji_retrieval/search/evidence.py
    - tests/test_search_api.py
  modified:
    - .gitignore
    - src/zyfangji_retrieval/domain/search_models.py
    - src/zyfangji_retrieval/search/service.py
    - src/zyfangji_retrieval/search/vector.py
    - src/zyfangji_retrieval/api/app.py
    - src/zyfangji_retrieval/api/routes/search.py
    - tests/test_search_pipeline.py
    - tests/test_search_contracts.py
key-decisions:
  - "Search responses now use query/results/warnings/metadata/score_semantics with retrieval_score and signal_scores, not legacy match_score/scores/pipeline names."
  - "BGE-M3 provider construction is lazy and fails as embedding_provider_unavailable during search, so health/status endpoints remain usable without endpoint configuration."
  - "Runtime app wiring uses BGE reranker by default; deterministic embedding/reranker paths are explicit test/dev settings only."
patterns-established:
  - "Formula code is projected from the first non-empty formula mention code without any business formulary join."
  - "Evidence fields come from normalized records with raw-record fallback for the western medicine priority header."
requirements-completed: [PIPE-01, PIPE-07, PIPE-08, RES-01, RES-02, RES-03, RES-04, RES-05]
duration: 13min
completed: 2026-06-14
---

# Phase 03 Plan 03: Java-Friendly Search Response Summary

**Evidence-rich hybrid search API response with lazy BGE-M3 wiring, stable Java error envelopes, bounded TopK, warnings, and score-safety semantics**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-14T17:22:35Z
- **Completed:** 2026-06-14T17:35:13Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added `search/evidence.py` to project `KnowledgeEntry` records into doctor-facing evidence fields, source metadata, formula identity, mapping status, and signal scores.
- Updated `SearchResponse` and `SearchResult` to the Java-facing contract: `query`, `results`, `warnings`, `metadata`, `score_semantics`, `retrieval_score`, `formula_code`, and `signal_scores`.
- Wired `create_app()` to attach a concrete `SearchService` using SQLite stores, BM25, Qdrant, lazy BGE-M3 embedding construction, and configured reranker selection.
- Added route-level error translation for index, vector store, embedding provider, reranker, validation, and unexpected search failures.
- Added endpoint tests for default Top10, explicit TopK, TopK validation, broad/sparse warnings, score semantics, provider config failures, and status/health survivability.

## Task Commits

1. **Task 1 RED: Add failing evidence response contract tests** - `c69e1ec` (`test`)
2. **Task 1 GREEN: Project evidence-rich SearchResult records** - `5978ce2` (`feat`)
3. **Task 2: Wire real search service into FastAPI and translate errors** - `c873d5f` (`feat`)
4. **Task 3: Verify TopK, warnings, score semantics, and endpoint contract** - `be9c65d` (`test`)

## Files Created/Modified

- `src/zyfangji_retrieval/search/evidence.py` - Evidence and SearchResult projection helpers.
- `tests/test_search_api.py` - API and service contract tests for evidence, provider wiring, TopK, warnings, and score semantics.
- `src/zyfangji_retrieval/domain/search_models.py` - Java-facing search response/result/evidence/metadata schemas.
- `src/zyfangji_retrieval/search/service.py` - Final response assembly using projected results and typed provider details.
- `src/zyfangji_retrieval/search/vector.py` - Lazy embedding provider factory support.
- `src/zyfangji_retrieval/api/app.py` - Concrete SearchService, Qdrant, BM25, embedding, and reranker wiring.
- `src/zyfangji_retrieval/api/routes/search.py` - SearchServiceError to stable HTTP envelope mapping.
- `tests/test_search_pipeline.py` - Existing pipeline assertions updated for the final response schema.
- `tests/test_search_contracts.py` - Existing route/schema assertions updated for app-level SearchService wiring.
- `.gitignore` - Ignores local runtime `var/` metadata/index artifacts generated by app/test startup.

## Decisions Made

- Kept formula-code projection limited to `formula_mentions`; no customer formulary, MySQL, prescription composition, or advice lookup was added.
- Search-time embedding construction is lazy because app startup and status checks must not require a configured BGE-M3 endpoint.
- Unknown `SearchServiceError` codes are normalized to `search_internal_error` with HTTP 500; known operational failures remain HTTP 503.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated prior tests to the final response schema**
- **Found during:** Task 1
- **Issue:** Existing Phase 3 tests still asserted legacy `query_text`, `pipeline`, `match_score`, `scores`, and evidence-embedded formula fields after the plan required the Java-facing final contract.
- **Fix:** Updated tests to assert `query.text`, `metadata`, `retrieval_score`, `signal_scores`, `entry_id`, and top-level formula/source fields.
- **Files modified:** `tests/test_search_pipeline.py`, `tests/test_search_contracts.py`
- **Verification:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py -q`
- **Committed in:** `5978ce2`, `c873d5f`

**2. [Rule 3 - Blocking] Ignored runtime metadata/index artifacts**
- **Found during:** Task 2
- **Issue:** Wiring the real SearchService into `create_app()` causes local SQLite metadata paths under `var/` to be created during tests, leaving generated files untracked.
- **Fix:** Added `var/` to `.gitignore` and removed the generated local artifacts.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` shows only the intentionally untracked `data/` directory after cleanup.
- **Committed in:** `c873d5f`

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking generated-artifact issue)
**Impact on plan:** Both were required to keep the final API contract and repository hygiene correct; no product scope was added.

## Issues Encountered

- `qdrant-client` emits compatibility warnings when local Qdrant is not running during tests that instantiate the real app. Tests still pass because non-search endpoints and lazy provider failure behavior are what this plan verifies.
- The package-level `zyfangji_retrieval.api.app` export shadows the `api.app` module name in normal import syntax, so API tests use `importlib.import_module("zyfangji_retrieval.api.app")` when monkeypatching app builders.

## Known Stubs

None. Nullable fields and empty lists found during the stub scan are Pydantic defaults or test fakes and do not block the plan goal.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: provider_boundary | `src/zyfangji_retrieval/api/app.py` | Wires the configured embedding and reranker providers into the Java-facing search path. Mitigations: provider construction is lazy, deterministic fallback is explicit only, and route/service errors do not include patient request bodies. |
| threat_flag: network_endpoint | `src/zyfangji_retrieval/api/routes/search.py` | Finalizes error translation at the `/api/search` trust boundary. Mitigations: stable envelope codes, validation envelope, and unknown error normalization. |

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q` -> 58 passed, 18 warnings (`fastapi` TestClient/httpx2 deprecation, `jieba` pkg_resources deprecation, and Qdrant compatibility warnings when no local Qdrant server is running).
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` -> All checks passed.

## User Setup Required

- Configure `ZYFANGJI_EMBEDDING_ENDPOINT_URL` and optional `ZYFANGJI_EMBEDDING_API_KEY` before production use with `embedding_provider=bge_m3`.
- Run/provision Qdrant at `ZYFANGJI_QDRANT_URL` and ensure an active index exists before real `/api/search` calls.
- Provision BGE reranker runtime/model access for `reranker_provider=bge`; deterministic reranker remains test/dev only.

## Next Phase Readiness

Phase 4 can now validate quality, safety, and performance against the complete endpoint contract. The API surface is ready for documentation/demo work: Java clients receive stable request validation, operational error envelopes, TopK metadata, evidence fields, and score semantics.

## Self-Check: PASSED

- Found summary and key implementation files.
- Found task commits `c69e1ec`, `5978ce2`, `c873d5f`, and `be9c65d` in git history.

---
*Phase: 03-hybrid-search-and-rerank-api*
*Completed: 2026-06-14*
