---
phase: 02-index-lifecycle-and-status
plan: 01
subsystem: indexing
tags: [qdrant, embeddings, pydantic-settings, vector-index, pytest]

requires:
  - phase: 01-local-data-contract-and-ingestion
    provides: KnowledgeEntry records and load_entries_for_rebuild source contract
provides:
  - Swappable embedding provider boundary with deterministic local provider
  - Shared index build, active index, validation, and status models
  - Qdrant versioned collection repository with canonical KnowledgeEntry payload mapping
  - Unit tests for provider validation and Qdrant indexing without Docker or network services
affects: [02-index-lifecycle-and-status, 03-hybrid-search-and-rerank-api]

tech-stack:
  added: [qdrant-client==1.18.0, bm25s==0.3.9, jieba==0.42.1, fastapi==0.136.3, uvicorn==0.49.0, pydantic-settings==2.14.1]
  patterns: [EmbeddingProvider protocol, deterministic provider tests, Qdrant repository boundary, versioned collection naming]

key-files:
  created:
    - src/zyfangji_retrieval/config.py
    - src/zyfangji_retrieval/domain/index_models.py
    - src/zyfangji_retrieval/indexing/__init__.py
    - src/zyfangji_retrieval/indexing/embeddings.py
    - src/zyfangji_retrieval/indexing/qdrant_store.py
    - tests/test_embedding_provider.py
    - tests/test_qdrant_indexing.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Use deterministic local embeddings for Phase 2 tests; no external BGE-M3 API calls are made in unit tests."
  - "Keep all Qdrant operations behind QdrantVectorIndex so later lifecycle and API code can inject fakes."
  - "Expose reranker fields in IndexStatus as not_configured placeholders because execution is Phase 3 scope."

patterns-established:
  - "EmbeddingProvider: provider implementations expose provider_id, model_id, vector_size, and embed_documents."
  - "Qdrant payloads project only canonical KnowledgeEntry fields needed for retrieval evidence and omit secrets/config dumps."
  - "Vector shape validation runs before any Qdrant upsert to prevent partial writes from malformed provider output."

requirements-completed: [IDX-01, IDX-04, IDX-05]

duration: 6m12s
completed: 2026-06-14
---

# Phase 02 Plan 01: Embedding Boundary and Qdrant Repository Summary

**BGE-M3-compatible provider boundary and versioned Qdrant vector indexing contracts for local KnowledgeEntry records**

## Performance

- **Duration:** 6m12s
- **Started:** 2026-06-14T14:51:15Z
- **Completed:** 2026-06-14T14:57:27Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added centralized `AppSettings` defaults for metadata DB, Qdrant, embeddings, BM25 index paths, and API title.
- Added shared index lifecycle/status models including Phase 2 reranker status fields set to `not_configured`.
- Added deterministic embedding provider and batch validation with explicit count/dimension failures.
- Added Qdrant payload mapping and a versioned vector repository for collection creation, pre-upsert validation, count validation, and alias activation.
- Added tests that use deterministic provider behavior and a fake Qdrant client, so no Docker, network Qdrant server, or real embedding API key is required.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing embedding provider tests** - `5514525` (test)
2. **Task 1 GREEN: Implement embedding provider boundary** - `fd16518` (feat)
3. **Task 2 RED: Add failing Qdrant indexing tests** - `4e78556` (test)
4. **Task 2 GREEN: Implement Qdrant vector repository** - `ac1e7c1` (feat)

## Files Created/Modified

- `pyproject.toml` - Added Phase 2 runtime dependencies.
- `uv.lock` - Locked the Phase 2 dependency graph.
- `src/zyfangji_retrieval/config.py` - Added environment-backed application/index settings.
- `src/zyfangji_retrieval/domain/index_models.py` - Added embedding batch, build, active index, status, and validation models.
- `src/zyfangji_retrieval/indexing/__init__.py` - Exported indexing provider and Qdrant repository symbols.
- `src/zyfangji_retrieval/indexing/embeddings.py` - Added provider protocol, deterministic provider, and validation errors.
- `src/zyfangji_retrieval/indexing/qdrant_store.py` - Added canonical payload projection and Qdrant vector repository.
- `tests/test_embedding_provider.py` - Covered provider metadata, vector validation, settings defaults, and status serialization.
- `tests/test_qdrant_indexing.py` - Covered payload mapping, collection naming, validation-before-upsert, and fake-client repository behavior.

## Decisions Made

- Deterministic embeddings are the only shipped provider implementation in this plan; real BGE-M3 provider selection remains behind the provider boundary.
- Qdrant repository tests use a fake client rather than a live service to keep unit tests local and deterministic.
- `IndexStatus` includes reranker fields now but reports `reranker_enabled=False`, `reranker_model_id=None`, and `reranker_status="not_configured"` until Phase 3.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv add` created a local `.venv` and emitted a cross-filesystem copy warning; `.venv` is ignored and no generated environment files were committed.
- Existing `.planning/STATE.md` modifications and untracked `data/` were present before task edits and were left untouched per orchestrator instructions.

## Known Stubs

None. Stub scan only found ordinary local empty list/dict initializers in tests and implementation accumulators.

## Authentication Gates

None.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_embedding_provider.py -q` - passed
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_qdrant_indexing.py -q` - passed
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_embedding_provider.py tests/test_qdrant_indexing.py -q` - passed, 10 tests
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` - passed

## Next Phase Readiness

Plan 02-02 can build on `EmbeddingProvider`, `IndexValidationResult`, and `QdrantVectorIndex` to orchestrate full rebuild, BM25 persistence, validation, and activation state. No Phase 3 patient query, fusion, or ranked result API was added.

## Self-Check: PASSED

- Created files verified on disk.
- Task commits verified in git history: `5514525`, `fd16518`, `4e78556`, `ac1e7c1`.

---
*Phase: 02-index-lifecycle-and-status*
*Completed: 2026-06-14*
