---
phase: 04-quality-safety-and-performance-validation
verified: 2026-06-16T13:32:00Z
status: human_needed
score: 5/5 must-haves verified by offline automation
overrides_applied: 0
human_verification:
  - test: "Run latency harness against live /api/search with real active Qdrant index, configured BGE-M3 embedding provider, and BGE-Reranker-v2-m3"
    expected: "Warm indexed search reports P50 < 500ms and P95 < 1s for the MVP sample corpus, excluding import, index rebuild, and corpus embedding generation"
    why_human: "Repository automation uses deterministic offline doubles; real provider/model/network/runtime latency requires the demo environment"
  - test: "Doctor/customer review of smoke query rankings for the sample Shanghanlun index"
    expected: "Common symptom, tongue, pulse, formula, article, and broad/sparse queries return useful ranked formula candidates with source evidence and risk fields visible"
    why_human: "Clinical usefulness and ranking adequacy require representative live data and domain review"
---

# Phase 4: Quality, Safety, and Performance Validation Report

**Phase Goal:** System behavior is regression-tested against real TCM query patterns, v1 safety boundaries, provider failures, stale-index failures, and MVP latency expectations.
**Verified:** 2026-06-16T13:32:00Z
**Status:** human_needed

## Goal Achievement

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Automated tests cover Excel parsing, canonical normalization, stable ID generation, retrieval-text construction, query construction, and response schema. | VERIFIED | `tests/test_quality_regression_contract.py` connects sample workbook mapping, canonical entry fields, retrieval text, `PatientSearchRequest`, and `SearchResponse`. |
| 2 | Smoke/regression queries cover common symptom, formula, article, tongue, pulse, and broad/sparse query paths. | VERIFIED | `tests/fixtures/smoke_queries.json` defines seven checked-in cases; `tests/test_smoke_queries.py` executes every case offline. |
| 3 | Source evidence and contraindication/risk fields are foregrounded in API/demo-style output. | VERIFIED | Quality and smoke tests assert result source, evidence fields, contraindication, and western-medicine-priority visibility where present. |
| 4 | Generated medical advice, autonomous diagnosis, prescribing, confidence, and certainty fields stay out of v1 responses. | VERIFIED | Recursive banned-key scans are present in both Phase 4 quality and smoke regression tests. |
| 5 | Indexed search latency can be measured repeatably with P50/P95 thresholds separated from import/index/build time. | VERIFIED / HUMAN CHECK | `scripts/search_latency.py` reports JSON P50/P95/max and thresholds offline; live demo-host latency still requires configured service/provider runtime. |

**Score:** 5/5 must-haves verified by repository automation; live latency/ranking checks still require human environment validation.

## Automated Verification

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py tests/test_quality_regression_contract.py tests/test_smoke_queries.py -q` | `147 passed, 18 warnings` |
| `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline` | `thresholds_passed: true`, P50 0.065 ms, P95 0.113 ms, max 0.406 ms |
| `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts` | All checks passed |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| QUAL-01 | SATISFIED | Cross-cutting quality regression tests over ingestion/query/response contract. |
| QUAL-02 | SATISFIED / HUMAN REVIEW | Checked-in smoke cases and offline runner exist; domain ranking anchors still need doctor/customer review on live sample index. |
| QUAL-03 | SATISFIED / HUMAN REVIEW | Automated evidence/risk field checks pass; live demo output should still be reviewed for usefulness. |
| QUAL-04 | SATISFIED | Recursive banned-field assertions verify v1 does not expose generated advice/diagnosis/prescribing/confidence fields. |
| QUAL-05 | SATISFIED / HUMAN CHECK | Latency harness exists and offline threshold sample passes; real demo-host `/api/search` latency remains manual. |

## Human Verification Required

### 1. Live Search Latency

**Test:** Configure the demo environment with active sample index, Qdrant, BGE-M3 embedding endpoint, and BGE-Reranker-v2-m3, then run:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode live --base-url http://127.0.0.1:8000 --enforce-thresholds
```

**Expected:** JSON reports `thresholds_passed: true`, P50 < 500 ms, and P95 < 1000 ms.

### 2. Domain Ranking Review

**Test:** Review live results for the seven smoke cases against the real sample Shanghanlun index.
**Expected:** Results expose formula, source article, evidence, contraindication/risk fields, and useful ordering for doctor-facing demo review.

## Gaps Summary

No repository code gaps remain for Phase 4. Status is `human_needed` because live provider/runtime latency and clinical ranking adequacy cannot be fully proven from deterministic offline tests.

---

_Verified: 2026-06-16T13:32:00Z_
_Verifier: Codex (gsd-execute-phase)_
