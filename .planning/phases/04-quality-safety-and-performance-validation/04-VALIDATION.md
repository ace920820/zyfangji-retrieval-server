---
phase: 04
slug: quality-safety-and-performance-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-16
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for quality, safety, smoke regression, provider failure, stale-index, and latency validation.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.0 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_quality_regression_contract.py tests/test_smoke_queries.py tests/test_search_api.py tests/test_search_pipeline.py -q` |
| **Full suite command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py tests/test_quality_regression_contract.py tests/test_smoke_queries.py -q` |
| **Latency command** | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline` |
| **Estimated runtime** | ~5 seconds focused after Wave 0, ~15 seconds full, latency runtime depends on sample count |

---

## Sampling Rate

- **After every task commit:** Run the Phase 4 quick command above.
- **After every plan wave:** Run the Phase 4 quick command plus `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts`.
- **Before `/gsd-verify-work`:** Run the full suite and latency command.
- **Max feedback latency:** 20 seconds for automated tests; latency command may be reported separately.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | QUAL-01 | T-04-01 / regression coverage | Cross-cutting test proves workbook parsing, canonical normalization, stable IDs, retrieval text, query construction, and response schema remain coherent without duplicating Phase 1-3 unit tests. | unit/contract | `pytest tests/test_quality_regression_contract.py -q` | yes | green |
| 04-01-02 | 01 | 1 | QUAL-03 / QUAL-04 | T-04-02 / medical safety boundary | API/demo-style responses foreground source/evidence/contraindication fields and do not expose generated diagnosis, advice, confidence, or autonomous prescription fields. | safety/negative contract | `pytest tests/test_quality_regression_contract.py tests/test_search_api.py -q` | yes | green |
| 04-01-03 | 01 | 1 | QUAL-04 | T-04-03 / provider failure leakage | Provider/vector/reranker/stale-index failures produce stable sanitized errors and do not leak patient text or present stale partial results. | API/service failure | `pytest tests/test_quality_regression_contract.py tests/test_search_pipeline.py tests/test_status_api.py -q` | yes | green |
| 04-02-01 | 02 | 2 | QUAL-02 / QUAL-03 / QUAL-04 | T-04-04 / smoke regression | Checked-in smoke queries for headache, fever, aversion to wind, no sweat, tongue, pulse, formula, article/broad query paths return comparable ranked results and safety fields. | regression/smoke | `pytest tests/test_smoke_queries.py -q` | yes | green |
| 04-02-02 | 02 | 2 | QUAL-05 | T-04-05 / latency availability | Repeatable latency harness reports P50/P95 for indexed `/api/search`, excludes import/corpus embedding, and separates offline deterministic from live provider mode. | performance report | `python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline` | yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/fixtures/smoke_queries.json` - smoke/regression query definitions for QUAL-02 and QUAL-05.
- [x] `tests/test_quality_regression_contract.py` - cross-cutting regression, evidence visibility, safety negative assertions, and handoff failure checks.
- [x] `tests/test_smoke_queries.py` - offline smoke query runner over deterministic in-memory service behavior.
- [x] `scripts/search_latency.py` - JSON-emitting P50/P95 latency harness with offline and live modes.
- [x] Optional `04-HUMAN-UAT.md` or VERIFICATION human section - live Qdrant/BGE-M3/reranker latency and ranking-quality checks when environment is available.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live BGE-M3/Qdrant/BGE-reranker latency on demo host | QUAL-05 | Repository tests cannot prove provider/network/model latency. | Configure active sample index, Qdrant, embedding endpoint, and reranker; run live latency mode and confirm P50 < 500ms and P95 < 1s or document blocker. |
| Doctor/customer review of smoke query ranking anchors | QUAL-02 / QUAL-03 | Clinical usefulness cannot be fully proven by deterministic technical assertions. | Review smoke query results for common symptoms and update fixture anchors only after approval. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 20s for automated suite
- [x] Latency report command exists and prints P50/P95 JSON
- [x] `nyquist_compliant: true` set in frontmatter after execution validates all requirements

**Approval:** automated validation complete; live/manual checks tracked in `04-HUMAN-UAT.md`

---

## Validation Audit 2026-06-16T13:35:33Z

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Coverage classification:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| QUAL-01 | COVERED | `tests/test_quality_regression_contract.py` covers workbook parsing, canonical entry shape, retrieval text, patient query construction, and response schema. |
| QUAL-02 | COVERED | `tests/fixtures/smoke_queries.json` and `tests/test_smoke_queries.py` cover symptom, tongue, pulse, formula, article/source, and broad/sparse smoke cases. |
| QUAL-03 | COVERED | Quality and smoke tests require source, evidence, contraindication, and western-medicine-priority fields where present. |
| QUAL-04 | COVERED | Recursive banned-key checks reject generated diagnosis, medical advice, autonomous prescription, treatment plan, and confidence fields. |
| QUAL-05 | COVERED | `scripts/search_latency.py` reports offline/live P50/P95 latency JSON with threshold pass/fail; live demo-host checks remain manual-only. |

Audit verification:

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_quality_regression_contract.py tests/test_smoke_queries.py -q` -> 14 passed, 1 warning.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline --runs 2 --warmups 1` -> thresholds passed; P50 0.066 ms, P95 0.106 ms.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check tests/test_quality_regression_contract.py tests/test_smoke_queries.py scripts/search_latency.py` -> All checks passed.

Decision: Phase 4 remains Nyquist-compliant. No additional validation tests were generated.
