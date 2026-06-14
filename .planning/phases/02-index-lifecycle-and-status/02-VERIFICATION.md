---
phase: 02-index-lifecycle-and-status
verified: 2026-06-14T15:29:36Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 2: Index Lifecycle and Status Verification Report

**Phase Goal:** System can build, validate, activate, and inspect local Qdrant/BM25 indexes without relying on customer business databases.
**Verified:** 2026-06-14T15:29:36Z
**Status:** passed
**Re-verification:** No

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | System builds an independent retrieval index from normalized local knowledge entries rather than searching a customer business database directly. | VERIFIED | `IndexLifecycleService.rebuild()` loads via `load_entries_for_rebuild(self.db_path, index_version=self.metadata_version)` and tests monkeypatch that path only. See [lifecycle.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/lifecycle.py:37>) and [test_index_lifecycle.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_index_lifecycle.py:272>). |
| 2 | System supports a full index rebuild that creates a new index version and activates it only after build validation succeeds. | VERIFIED | `build_index_version()` uses unique microsecond timestamps; lifecycle marks validated before alias activation and SQLite activation. See [lifecycle.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/lifecycle.py:16>) and [index_state.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/persistence/index_state.py:126>). |
| 3 | System exposes index/status data including readiness, active version, indexed count, model/provider identifiers, last build time, and last error. | VERIFIED | `IndexStatusService.status()` fills those fields from SQLite active/latest build records, and CLI/API tests assert them. See [status.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/status.py:11>) and [test_status_api.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_status_api.py:63>). |
| 4 | System supports BGE-M3 semantic embeddings through a swappable embedding-provider interface. | VERIFIED | `EmbeddingProvider` is a protocol; `DeterministicEmbeddingProvider` is the local implementation used in tests and CLI defaults. See [embeddings.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/embeddings.py:12>) and [test_embedding_provider.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_embedding_provider.py:18>). |
| 5 | System writes dense vectors and payload metadata to Qdrant for vector recall. | VERIFIED | `build_qdrant_payload()` projects canonical `KnowledgeEntry` fields and `QdrantVectorIndex.upsert_entries()` validates shapes before writing points. See [qdrant_store.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/qdrant_store.py:17>) and [test_qdrant_indexing.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_qdrant_indexing.py:83>). |
| 6 | System supports BM25-style lexical retrieval with Chinese tokenization for exact symptoms, aliases, formula names, tongue/pulse terms, and article references. | VERIFIED | `tokenize_chinese_text()` loads the project TCM dictionary and `BM25IndexStore` builds versioned local indexes from retrieval text plus exact formula/article fields. See [tokenizer.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/tokenizer.py:25>) and [bm25_store.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/bm25_store.py:36>). |
| 7 | System exposes a lightweight status endpoint with embedding model, reranker model, vector store, retrieval strategy, knowledge count, index version, and update time. | VERIFIED | `IndexStatus` includes those contract fields, and `/status` plus `index-status` return them. See [index_models.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/domain/index_models.py:54>) and [status.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/api/routes/status.py:28>). |
| 8 | System exposes a health/readiness endpoint suitable for deployment and Java-backend integration checks. | VERIFIED | `/health/live` and `/health/ready` are read-only GET endpoints; readiness returns 503 when counts are inconsistent. See [status.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/api/routes/status.py:23>) and [test_status_api.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_status_api.py:200>). |
| 9 | Import and rebuild failures are visible through API responses or status output instead of failing silently. | VERIFIED | Latest failed build error is surfaced in status JSON, and readiness failure returns `HTTPException(503, detail=status.model_dump(mode="json"))`. See [status.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/status.py:63>) and [status route](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/api/routes/status.py:33>). |
| 10 | Embedding or reranker provider failures return clear errors and do not present stale or partial results as fresh matches. | VERIFIED | Embedding validation raises explicit errors, lifecycle marks failed builds, and previous active state stays intact after failures. Reranker is explicitly `not_configured` in Phase 2. See [embeddings.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/src/zyfangji_retrieval/indexing/embeddings.py:54>) and [test_index_lifecycle.py](</Volumes/KINGSTON/projects/zyfangji-retrieval-server/tests/test_index_lifecycle.py:362>). |

**Score:** 10/10 truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/zyfangji_retrieval/config.py` | centralized index/Qdrant/provider settings | VERIFIED | `AppSettings` exposes all Phase 2 defaults. |
| `src/zyfangji_retrieval/domain/index_models.py` | shared build/status/validation models | VERIFIED | Includes `EmbeddingBatchResult`, `IndexBuildRecord`, `ActiveIndexRecord`, `IndexStatus`, `IndexValidationResult`. |
| `src/zyfangji_retrieval/indexing/embeddings.py` | provider boundary and batch validation | VERIFIED | Protocol + deterministic provider + explicit validation errors. |
| `src/zyfangji_retrieval/indexing/qdrant_store.py` | Qdrant payload mapping and versioned repository | VERIFIED | Payload projection, collection naming, validation, alias activation. |
| `src/zyfangji_retrieval/indexing/tokenizer.py` | Chinese tokenization and TCM dictionary loading | VERIFIED | `jieba` terms are loaded from bundled dictionary. |
| `src/zyfangji_retrieval/indexing/bm25_store.py` | versioned BM25 persistence | VERIFIED | Build/load/validate implemented and tested. |
| `src/zyfangji_retrieval/persistence/index_state.py` | SQLite build ledger and active index truth | VERIFIED | Build, validate, fail, and activate transitions persist locally. |
| `src/zyfangji_retrieval/indexing/lifecycle.py` | rebuild/validate/activate orchestration | VERIFIED | Local rebuild flow gates activation on validation. |
| `src/zyfangji_retrieval/indexing/status.py` | status builder from local state | VERIFIED | Reads SQLite active/latest build only. |
| `src/zyfangji_retrieval/api/app.py` | FastAPI app factory | VERIFIED | Includes read-only status router. |
| `src/zyfangji_retrieval/api/routes/status.py` | liveness/readiness/status endpoints | VERIFIED | GET-only surface. |
| `src/zyfangji_retrieval/cli.py` | operator commands | VERIFIED | `index-rebuild`, `index-validate`, and `index-status` are present. |

## Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `lifecycle.py` | `ingestion/importer.py` | `load_entries_for_rebuild(db_path, index_version=metadata_version)` | VERIFIED | Local metadata rebuild path confirmed. |
| `lifecycle.py` | `persistence/index_state.py` | build/validate/fail/activate transitions | VERIFIED | SQLite is the single source of active truth. |
| `lifecycle.py` | `qdrant_store.py` | `QdrantVectorIndex` methods | VERIFIED | Create, upsert, validate, and alias activation are wired. |
| `lifecycle.py` | `bm25_store.py` | `BM25IndexStore` methods | VERIFIED | BM25 build and validation are wired into rebuild. |
| `status.py` | `persistence/index_state.py` | `get_active()` / `get_latest_build()` | VERIFIED | Status is derived from SQLite only. |
| `api/routes/status.py` | `indexing/status.py` | `IndexStatusService` | VERIFIED | HTTP status shares the same status contract as CLI. |
| `cli.py` | `indexing/status.py` | `index-status` JSON output | VERIFIED | CLI emits the same Phase 2 fields. |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| IDX-01 | 02-PLAN.md | independent retrieval index from local knowledge entries | SATISFIED | `load_entries_for_rebuild()` only, no customer DB path in lifecycle tests. |
| IDX-02 | 02-PLAN.md | full rebuild, new version, validation-gated activation | SATISFIED | `build_index_version()`, `mark_validated()`, then alias activation and SQLite activation. |
| IDX-03 | 02-03-PLAN.md | status data including readiness, active version, count, providers, build time, last error | SATISFIED | `IndexStatusService` and `/status`/`index-status` output. |
| IDX-04 | 02-01-PLAN.md | swappable embedding-provider interface | SATISFIED | `EmbeddingProvider` protocol and deterministic implementation. |
| IDX-05 | 02-01-PLAN.md | dense vectors and payload metadata to Qdrant | SATISFIED | `build_qdrant_payload()` + `upsert_entries()` with shape validation. |
| IDX-06 | 02-02-PLAN.md | BM25 retrieval with Chinese tokenization | SATISFIED | `jieba` tokenizer + versioned BM25 artifacts. |
| STAT-01 | 02-03-PLAN.md | status endpoint fields including model, reranker, vector store, retrieval strategy, count, version, update time | SATISFIED | `IndexStatus` contract and `/status`/CLI output. |
| STAT-02 | 02-03-PLAN.md | health/readiness endpoint | SATISFIED | `/health/live` and `/health/ready`. |
| STAT-03 | 02-03-PLAN.md | failures visible instead of silent | SATISFIED | `last_error` surfaced and readiness returns 503 with JSON detail. |
| STAT-04 | 02-02-PLAN.md / 02-03-PLAN.md | provider failures clear, no stale/partial results as fresh matches | SATISFIED | failures mark build failed, previous active stays intact, reranker remains not configured. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 2 regression suite | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py -q` | 82 passed, 1 deprecation warning | PASS |
| Lint check | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` | All checks passed | PASS |

## Anti-Patterns Found

None blocking. One non-blocking warning remains from FastAPI/Starlette testclient deprecation in the test environment.

## Human Verification Required

None.

## Gaps Summary

No blocking gaps found. Phase 2 goal is achieved: local metadata rebuilds can create, validate, activate, and inspect versioned Qdrant/BM25 indexes without using customer business databases, and all Phase 2 requirement IDs are accounted for.

---

_Verified: 2026-06-14T15:29:36Z_
_Verifier: Claude (gsd-verifier)_
