---
phase: 03-hybrid-search-and-rerank-api
plan: 02
subsystem: search
tags: [bm25, qdrant, bge-m3, rrf, rerank, fastapi]
requires:
  - phase: 03-hybrid-search-and-rerank-api
    plan: 01
    provides: "Search request/response contracts and POST /api/search route"
provides:
  - "Active-index-gated BM25 Top50 and Qdrant vector Top50 recall"
  - "HTTP BGE-M3 embedding provider factory with explicit deterministic fallback only"
  - "RRF fusion and BGE-Reranker-v2-m3 provider boundary"
  - "SearchService orchestration with typed embedding/reranker/index readiness failures"
affects: [03-hybrid-search-and-rerank-api, 04-quality-safety-and-performance-validation, 05-documentation-and-demo-delivery]
tech-stack:
  added: ["FlagEmbedding==1.4.0"]
  patterns: ["Active SQLite index as search source of truth", "RRF over heterogeneous ranks", "Provider errors without patient-text leakage"]
key-files:
  created:
    - src/zyfangji_retrieval/search/bm25.py
    - src/zyfangji_retrieval/search/embedding_factory.py
    - src/zyfangji_retrieval/search/vector.py
    - src/zyfangji_retrieval/search/fusion.py
    - src/zyfangji_retrieval/search/rerank.py
    - src/zyfangji_retrieval/search/service.py
    - tests/test_search_pipeline.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/zyfangji_retrieval/config.py
    - src/zyfangji_retrieval/domain/search_models.py
    - src/zyfangji_retrieval/api/routes/search.py
    - tests/test_search_contracts.py
key-decisions:
  - "Search uses SQLite active index records for BM25 path, Qdrant collection, and metadata version instead of Qdrant alias discovery."
  - "BGE-M3 runtime mode fails typed when endpoint configuration is missing or unavailable; deterministic embeddings are only selected by explicit provider setting."
  - "Reranker is required by default, with a configured degraded fused-results fallback only when reranker_required is false."
requirements-completed: [PIPE-03, PIPE-04, PIPE-05, PIPE-06]
duration: 24min
completed: 2026-06-14
---

# Phase 03 Plan 02: Hybrid Search Pipeline Summary

**BM25 + BGE-M3 vector recall with RRF fusion and BGE reranker orchestration behind the search contract**

## Performance

- **Duration:** 24 min
- **Started:** 2026-06-14T16:49:43Z
- **Completed:** 2026-06-14T17:13:18Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Added BM25 recall from `ActiveIndexRecord.bm25_path` and `index_version`, using project Chinese tokenization and `snapshot.metadata.entry_ids` to preserve entry alignment.
- Added HTTP BGE-M3 embedding provider support for OpenAI-compatible `data[].embedding` and compact `embeddings` responses, including count/vector-size validation and no patient text in provider errors.
- Added Qdrant vector recall against `active.qdrant_collection` with payload return and Top50 limit propagation.
- Added RRF fusion that preserves BM25/vector rank and raw signal scores as diagnostics.
- Added BGE reranker provider boundary using `FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)` plus deterministic and disabled providers for explicit tests/dev behavior.
- Added `SearchService` orchestration from active index to metadata load, BM25/vector recall, fusion, rerank, evidence projection, and typed provider/index failure semantics.

## Task Commits

1. **Task 1: Implement BM25, configured BGE-M3 provider, and vector Top50 recall** - `688a89d` (`feat`)
2. **Task 2: Implement RRF fusion and real BGE reranker provider boundary** - `ae9b322` (`feat`)
3. **Task 3: Orchestrate active-index-gated SearchService** - `7cac29a` (`feat`)

## Files Created/Modified

- `src/zyfangji_retrieval/search/bm25.py` - Active BM25 snapshot loading and Top50 lexical candidates.
- `src/zyfangji_retrieval/search/embedding_factory.py` - BGE-M3 HTTP embedding provider, errors, and provider factory.
- `src/zyfangji_retrieval/search/vector.py` - Query embedding and active-collection Qdrant vector recall.
- `src/zyfangji_retrieval/search/fusion.py` - RRF/weighted candidate fusion with preserved signal diagnostics.
- `src/zyfangji_retrieval/search/rerank.py` - Reranker protocol, BGE provider, deterministic provider, and disabled provider.
- `src/zyfangji_retrieval/search/service.py` - End-to-end read-only search orchestration and evidence projection.
- `src/zyfangji_retrieval/config.py` - Added embedding provider timeout setting.
- `src/zyfangji_retrieval/domain/search_models.py` - Added pipeline status metadata.
- `src/zyfangji_retrieval/api/routes/search.py` - Converts `SearchServiceError` into stable 503 error envelopes.
- `pyproject.toml` / `uv.lock` - Added and locked `FlagEmbedding==1.4.0`.
- `tests/test_search_pipeline.py` - Deterministic pipeline, provider, fusion, reranker, and service tests.
- `tests/test_search_contracts.py` - Search route typed service-error contract test.

## Decisions Made

- Active SQLite index state is the only search resource source of truth; search does not discover active resources from Qdrant aliases.
- BGE-M3 provider configuration is strict: missing endpoint or provider errors return typed failures rather than fake deterministic semantic recall.
- RRF is the default fusion strategy because BM25, vector, and reranker scores remain diagnostic ranking signals, not calibrated medical confidence.
- Reranker failure is fatal by default (`reranker_unavailable`) and only degrades to fused ranking when `reranker_required=False`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Converted SearchService errors at the route boundary**
- **Found during:** Task 3
- **Issue:** The plan required typed provider failure behavior for `/api/search`, but `SearchServiceError` would otherwise propagate as an internal server error.
- **Fix:** Updated `src/zyfangji_retrieval/api/routes/search.py` to convert `SearchServiceError` into the existing stable `SearchErrorEnvelope`.
- **Files modified:** `src/zyfangji_retrieval/api/routes/search.py`, `tests/test_search_contracts.py`
- **Verification:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_pipeline.py tests/test_search_contracts.py -q`
- **Committed in:** `7cac29a`

**2. [Rule 1 - Bug] Corrected degraded-reranker test expectations for existing query warnings and RRF tie ordering**
- **Found during:** Task 3
- **Issue:** The first degraded-reranker test expected only `query_too_sparse` plus `reranker_degraded` and assumed vector-first ordering, but the query builder also emits `query_broad`, and RRF ties sort deterministically by `entry_id`.
- **Fix:** Updated the test to assert all warnings and the actual stable fused order.
- **Files modified:** `tests/test_search_pipeline.py`
- **Verification:** `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_pipeline.py tests/test_search_contracts.py -q`
- **Committed in:** `7cac29a`

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 test bug)
**Impact on plan:** Both changes preserve the planned API/error semantics and do not add product scope.

## Issues Encountered

- Adding `FlagEmbedding==1.4.0` triggered a large dependency resolution and download through `uv`, including Torch-related packages. This completed successfully and updated `uv.lock`.

## Known Stubs

None. Empty dictionaries/lists found by the stub scan are test fakes, response defaults, or deliberate error-envelope defaults; they do not block the plan goal.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: provider_boundary | `src/zyfangji_retrieval/search/embedding_factory.py` | Patient query text may cross the configured BGE-M3 embedding endpoint boundary. Mitigation: typed provider errors avoid patient-text leakage and deterministic fallback is explicit only. |
| threat_flag: provider_boundary | `src/zyfangji_retrieval/search/rerank.py` | Patient query text and candidate evidence may cross the BGE reranker boundary. Mitigation: provider errors are wrapped without raw query/evidence text. |

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_pipeline.py tests/test_search_contracts.py -q` -> 40 passed, 2 warnings (`jieba` pkg_resources warning; FastAPI TestClient deprecation warning).
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` -> All checks passed.

## User Setup Required

- Configure `ZYFANGJI_EMBEDDING_ENDPOINT_URL` and optional `ZYFANGJI_EMBEDDING_API_KEY` before using production `embedding_provider=bge_m3`.
- Provision local BGE reranker model dependencies for real reranker execution; unit tests use fakes and do not download model weights.

## Next Phase Readiness

Plan 03-03 can focus on result projection/API wiring polish and demo readiness. The pipeline now returns ranked `SearchResponse` objects with source evidence, diagnostic score fields, pipeline metadata, and explicit provider failure semantics.

## Self-Check: PASSED

- Found summary and key implementation files.
- Found task commits `688a89d`, `ae9b322`, and `7cac29a` in git history.

---
*Phase: 03-hybrid-search-and-rerank-api*
*Completed: 2026-06-14*
