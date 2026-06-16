---
phase: 04-quality-safety-and-performance-validation
plan: 01
subsystem: quality
tags: [pytest, regression, safety, provider-failure, stale-index]
requires:
  - phase: 03-hybrid-search-and-rerank-api
    provides: "Search response contract, evidence projection, provider failure semantics, and score-safety boundaries"
provides:
  - "Cross-cutting ingestion-to-query-to-response regression coverage"
  - "Safety negative assertions for generated diagnosis/advice/prescribing fields"
  - "Provider/vector/reranker/stale-index failure leakage matrix"
affects: [04-quality-safety-and-performance-validation, 05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["Offline deterministic regression tests", "Recursive banned response-key scan", "Sanitized SearchServiceError assertions"]
key-files:
  created:
    - tests/test_quality_regression_contract.py
  modified: []
key-decisions:
  - "Phase 4 quality tests reuse existing public ingestion/search APIs rather than adding production-only test helpers."
  - "Safety checks recursively inspect JSON keys to avoid false positives from the required score-semantics sentence."
  - "Provider and stale-index checks stay offline and deterministic; live BGE/Qdrant/reranker validation remains opt-in/manual."
requirements-completed: [QUAL-01, QUAL-03, QUAL-04]
duration: 8min
completed: 2026-06-16
---

# Phase 04 Plan 01: Quality and Safety Regression Summary

**Cross-cutting offline regression tests for ingestion/query/response cohesion, evidence visibility, medical-safety boundaries, and sanitized failure handling**

## Performance

- **Duration:** 8 min
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Added `tests/test_quality_regression_contract.py`.
- Verified the real Shanghanlun workbook can still map into a canonical entry with stable `shl_` ID shape, preserved raw/normalized records, retrieval text, structured patient query text, and a `SearchResponse`.
- Added response safety assertions that require source, formula, evidence, contraindication, and western-medicine-priority fields.
- Added recursive banned-key checks for generated diagnosis, medical advice, autonomous prescription, confidence, and related unsafe fields.
- Added offline provider/vector/reranker/stale-index failure checks proving typed `SearchServiceError` codes without patient-text leakage.

## Task Commits

1. **Tasks 1-3: Add quality, safety, and failure regression tests** - `177c88f` (`test`)

## Files Created/Modified

- `tests/test_quality_regression_contract.py` - Cross-cutting Phase 4 regression tests.

## Deviations from Plan

None. The plan was implemented without adding production helpers or external-service dependencies.

## Known Stubs

None. Fake stores/retrievers/rerankers are test doubles used to keep the regression suite deterministic and offline.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: safety_boundary | `tests/test_quality_regression_contract.py` | Verifies responses foreground evidence/risk fields and omit generated medical-decision fields. |
| threat_flag: provider_boundary | `tests/test_quality_regression_contract.py` | Verifies provider/vector/reranker failure errors are sanitized and do not leak patient text. |

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_quality_regression_contract.py -q` -> 6 passed, 1 warning.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_quality_regression_contract.py tests/test_search_api.py tests/test_search_pipeline.py tests/test_status_api.py -q` -> 46 passed, 13 warnings.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check tests/test_quality_regression_contract.py` -> All checks passed.

## User Setup Required

None for automated validation. Live provider/Qdrant/reranker checks remain separate opt-in/manual work.

## Next Phase Readiness

Plan 04-02 can build the smoke query fixture and latency harness on top of the safety/failure assertions added here.

## Self-Check: PASSED

- Found summary and key implementation files.
- Found task commit `177c88f` in git history.
