---
phase: 03-hybrid-search-and-rerank-api
verified: 2026-06-14T17:43:16Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
post_review_fix:
  commit: "071c035"
  change: "Qdrant/vector-store failures now map to vector_store_unavailable"
  verification: "60 passed, 18 warnings"
human_verification:
  - test: "Run /api/search against a live active index with configured BGE-M3 embedding endpoint, Qdrant, and BGE-Reranker-v2-m3 provider"
    expected: "POST /api/search returns ranked TopK formula results after BM25 Top50 recall, Qdrant vector Top50 recall, hybrid fusion, and reranking without provider/index errors"
    why_human: "External provider/model and Qdrant runtime integration cannot be fully proven by repository-only static checks and deterministic unit tests"
  - test: "Inspect a real broad or sparse clinical query response from the sample Shanghanlun index"
    expected: "Response contains ranked results plus query-quality warnings, and score text is not presented as medical confidence or prescription certainty"
    why_human: "Ranking quality and doctor-facing usefulness require live sample data and human review"
---

# Phase 3: Hybrid Search and Rerank API Verification Report

**Phase Goal:** Java backend can submit patient presentation data and receive TopK ranked formula results produced by BM25 recall, vector recall, hybrid fusion, and BGE rerank.
**Verified:** 2026-06-14T17:43:16Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Java backend can call a stateless search endpoint with main symptom, symptom list, tongue, pulse, syndrome, and bounded `topk`. | VERIFIED | `PatientSearchRequest` defines the structured fields and `topk` bounds; `POST /api/search` is registered with `response_model=SearchResponse`; tests cover default and explicit TopK plus validation errors. |
| 2 | Search performs BM25 Top50 recall, BGE-M3 Qdrant Top50 recall, hybrid fusion, and BGE-Reranker-v2-m3 reranking before returning results. | VERIFIED | `SearchService.search()` calls `BM25Retriever.recall(... recall_topk=50)`, `VectorRetriever.recall(... recall_topk=50)`, `fuse_candidates(... limit=50)`, then `self.reranker.rerank(...)`; default settings use `embedding_provider="bge_m3"`, `reranker_provider="bge"`, `reranker_required=True`. |
| 3 | Search response returns Top10 by default with rank, retrieval score, `score_type`, `entry_id`, source metadata, formula fields, and mapping status. | VERIFIED | Pydantic response models include required fields; `project_search_result()` projects rank, score, source, formula raw/mentions/code, mapping status, and signal scores; tests assert default Top10 and Java-friendly shape. |
| 4 | Each result includes doctor-facing evidence fields such as symptoms, aliases, tongue, pulse, source article, syndrome, disease name, treatment method, contraindications, and efficacy assessment when present. | VERIFIED | `EvidenceFields` and `project_evidence()` include symptom, tongue, pulse, article, syndrome, disease, therapy, contraindication, effect, and western-medicine-priority fields from normalized/raw records; tests assert the projected JSON shape. |
| 5 | Broad or sparse queries return ranked results and optional query-quality warnings without presenting scores as medical confidence. | VERIFIED | `build_patient_query()` emits `query_too_sparse` and `query_broad`; `SearchResponse.score_semantics` says scores are ranking/reference signals only; tests assert warnings and absence of confidence/probability fields. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/zyfangji_retrieval/domain/search_models.py` | Request/response/result/warning/error schemas | VERIFIED | Exists, substantive, used by route, query builder, service, and tests. |
| `src/zyfangji_retrieval/search/query.py` | Structured patient fields to labeled query text and warnings | VERIFIED | Builds labeled query sections and query-quality warnings; covered by contract tests. |
| `src/zyfangji_retrieval/search/bm25.py` | BM25 Top50 recall from active BM25 artifact | VERIFIED | Loads active version from BM25 store and passes `k=recall_topk`; tested with fake BM25 store. |
| `src/zyfangji_retrieval/search/vector.py` | BGE-M3 query embedding plus Qdrant recall | VERIFIED | Embeds query, queries active Qdrant collection with `limit=recall_topk`, returns payload-backed candidates; tested with fake Qdrant client. |
| `src/zyfangji_retrieval/search/embedding_factory.py` | Real BGE-M3 HTTP provider and explicit deterministic fallback | VERIFIED | Default provider is BGE-M3 and missing endpoint fails clearly; deterministic provider is explicit only; tests cover response parsing and failure sanitization. |
| `src/zyfangji_retrieval/search/fusion.py` | RRF/weighted fusion | VERIFIED | Default RRF over BM25/vector ranks preserves diagnostic signal scores and limits fused candidates. |
| `src/zyfangji_retrieval/search/rerank.py` | BGE reranker provider boundary | VERIFIED | `BGERerankerProvider` lazily loads `FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)` and sorts by rerank score; deterministic/disabled providers are explicit alternatives. |
| `src/zyfangji_retrieval/search/service.py` | End-to-end active-index-gated orchestration | VERIFIED | Uses active index state, loads metadata, runs recall/fusion/rerank, projects results, and raises stable service errors. |
| `src/zyfangji_retrieval/search/evidence.py` | KnowledgeEntry to SearchResult/Evidence projection | VERIFIED | Projects formula identity, source metadata, evidence fields, score type, and signal scores without business formulary lookup. |
| `src/zyfangji_retrieval/api/routes/search.py` | POST `/api/search` and stable error translation | VERIFIED | Calls `app.state.search_service.search()` and translates known service errors to stable envelopes. |
| `tests/test_search_contracts.py`, `tests/test_search_pipeline.py`, `tests/test_search_api.py` | Phase 3 contract/pipeline/API tests | VERIFIED | 49 tests passed. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `api/app.py` | `api/routes/search.py` | `api.include_router(search_router)` | VERIFIED | Manual check confirmed route inclusion. The gsd regex expected a bare call and reported a false negative. |
| `api/routes/search.py` | `domain/search_models.py` | `response_model=SearchResponse` | VERIFIED | Tool and manual checks confirmed. |
| `search/query.py` | `domain/search_models.py` | `build_patient_query(request: PatientSearchRequest)` | VERIFIED | Manual check confirmed typed request input; tool regex was overly strict. |
| `search/service.py` | `persistence/index_state.py` | `self.index_store.get_active()` | VERIFIED | Manual check confirmed active index is the source of truth. |
| `search/bm25.py` | `indexing/bm25_store.py` | `BM25IndexStore.load(active.index_version)` | VERIFIED | Tool and manual checks confirmed. |
| `search/vector.py` | `indexing/embeddings.py` | `embed_documents([query_text])` | VERIFIED | Tool and manual checks confirmed. |
| `search/service.py` | `search/rerank.py` | Fused candidates passed to `self.reranker.rerank(...)` | VERIFIED | Manual check confirmed service passes fused candidates after recall and fusion. |
| `search/service.py` | `search/evidence.py` | `project_search_result()` | VERIFIED | Tool and manual checks confirmed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `SearchService` | `results` | Active index state, SQLite metadata, BM25 snapshot, Qdrant vector results, reranker scores | Yes in code path; live provider/index still needs environment verification | VERIFIED / HUMAN CHECK |
| `project_search_result()` | `evidence`, `formula_*`, `source`, `signal_scores` | `KnowledgeEntry` normalized/raw records plus fused/rerank candidates | Yes | VERIFIED |
| `/api/search` | `SearchResponse` | `app.state.search_service.search(request)` | Yes | VERIFIED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Phase 3 contract, pipeline, API, and status tests | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q` | `60 passed, 18 warnings` after post-review fix `071c035` | PASS |
| Artifact checks from PLAN frontmatter | `gsd-tools verify artifacts` for 03-01, 03-02, 03-03 | 13/13 artifacts passed | PASS |
| Key-link checks from PLAN frontmatter | `gsd-tools verify key-links` plus manual review | 10/10 links verified after correcting regex false negatives | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| PIPE-01 | 03-01, 03-03 | Stateless search endpoint with patient fields and `topk` | SATISFIED | `POST /api/search`, `PatientSearchRequest`, route tests. |
| PIPE-02 | 03-01 | Normalized labeled query text | SATISFIED | `build_patient_query()` and contract tests. |
| PIPE-03 | 03-02 | BM25 Top50 recall | SATISFIED | `BM25Retriever.recall()` passes `k=recall_topk`; tests assert 50. |
| PIPE-04 | 03-02 | BGE-M3 Qdrant Top50 vector recall | SATISFIED | `BgeM3HttpEmbeddingProvider`, `VectorRetriever.query_points(... limit=recall_topk)`; tests assert provider and limit behavior. |
| PIPE-05 | 03-02 | Hybrid fusion | SATISFIED | `fuse_candidates()` supports RRF default and weighted strategy. |
| PIPE-06 | 03-02 | BGE reranking | SATISFIED | Default app wiring builds `BGERerankerProvider`; service requires reranker by default. |
| PIPE-07 | 03-01, 03-03 | Top10 default and bounded caller TopK | SATISFIED | `topk` defaults to 10 and `le=50`; API tests cover default, explicit 2, and over-50 rejection. |
| PIPE-08 | 03-03 | Sparse/broad query warnings without certainty claims | SATISFIED | Query warnings and score semantics tests. |
| RES-01 | 03-03 | Rank, score, ID, source, formula, mapping fields | SATISFIED | `SearchResult` and `project_search_result()`; API tests assert JSON fields. |
| RES-02 | 03-03 | Doctor-facing evidence fields | SATISFIED | `EvidenceFields` and `project_evidence()`; tests assert all key evidence fields. |
| RES-03 | 03-01, 03-03 | Score semantics not medical confidence | SATISFIED | Response-level `score_semantics`; tests assert text and absence of confidence/probability fields. |
| RES-04 | 03-03 | Java-friendly response without business formulary fetch | SATISFIED | Formula code is first local mention code or null; no customer DB/formulary lookup in search/evidence/service. |
| RES-05 | 03-01, 03-03 | Stable JSON errors | SATISFIED | Validation, unavailable service, provider, reranker, and search-service errors covered by tests. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| None | - | No blocking placeholder/TODO/empty-handler/static-result anti-patterns found in Phase 3 files | - | - |

### Human Verification Required

### 1. Live Search Pipeline

**Test:** Run `/api/search` against a real activated sample index with BGE-M3 embedding endpoint, Qdrant, and BGE-Reranker-v2-m3 configured.
**Expected:** The endpoint returns TopK ranked formula results after BM25 recall, Qdrant vector recall, hybrid fusion, and reranking.
**Why human:** Repository tests use deterministic fakes for external dependencies; real provider/model and Qdrant runtime behavior need a configured environment.

### 2. Broad/Sparse Query Review

**Test:** Submit a short or broad real clinical query, inspect ranking and warnings.
**Expected:** Results are ranked, warnings are present when applicable, and scores are framed only as retrieval ranking/reference signals.
**Why human:** The code emits warnings, but ranking usefulness and doctor-facing adequacy require live sample data review.

### Gaps Summary

No code gaps found for Phase 3. Automated verification confirms the endpoint contract, BM25/vector recall orchestration, fusion, reranker wiring, response projection, error envelopes, and Phase 3 requirements PIPE-01 through PIPE-08 and RES-01 through RES-05. Overall status is `human_needed` because live external provider/Qdrant/model behavior and real-data ranking quality require manual verification.

---

_Verified: 2026-06-14T17:43:16Z_
_Verifier: Claude (gsd-verifier)_
