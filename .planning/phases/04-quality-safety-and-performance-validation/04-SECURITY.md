---
phase: 04
slug: quality-safety-and-performance-validation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-16
updated: 2026-06-16
---

# Phase 04 - Security

> Per-phase security/safety contract for quality regression, smoke validation, provider failure handling, and latency reporting.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Sample workbook -> regression tests | Real Shanghanlun workbook data is parsed for cross-cutting contract validation. | Source Excel row fields, normalized fields, retrieval text, and formula mapping status. |
| Search response -> API/demo consumers | Internal retrieval results become doctor-facing JSON. | Source, formula identity, evidence fields, contraindication/risk fields, signal scores, and score semantics. |
| Provider failure -> outward error checks | Simulated provider/vector/reranker failures cross into service errors. | Sanitized error code, message, details, and absence of patient text. |
| Smoke fixture -> test runner | Checked-in query expectations drive regression assertions. | Patient query payloads, must-have field paths, banned fields, and formula anchors. |
| Patient query payload -> live latency mode | Structured patient text crosses to a configured HTTP service only when explicitly opted in. | Fixture request JSON posted to `/api/search` in live mode. |
| Latency report -> demo stakeholders | Performance samples become auditable JSON. | P50/P95/max, thresholds, sample counts, mode, dataset size, index version, metadata version. |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01-01 | Tampering | `tests/test_quality_regression_contract.py` | mitigate | Test uses the real sample workbook path and existing ingestion mapper to avoid mock-only false positives for QUAL-01. | closed |
| T-04-01-02 | Information Disclosure | provider failure tests | mitigate | Test asserts private patient text is absent from `SearchServiceError` string, message, and details for embedding/vector/reranker failures. | closed |
| T-04-01-03 | Safety/Misuse | serialized `SearchResponse` | mitigate | Recursive banned-key scan rejects generated diagnosis, advice, prescribing, confidence, and certainty fields. | closed |
| T-04-01-04 | Safety/Misuse | evidence projection | mitigate | Tests require source, formula, mapping status, contraindication, and western-medicine-priority evidence fields when source data contains them. | closed |
| T-04-01-05 | Spoofing | active index readiness | mitigate | Missing/empty active index is tested to raise `index_not_ready` before any results are returned. | closed |
| T-04-01-06 | Repudiation | test coverage claims | mitigate | Verification and summaries explicitly separate deterministic offline validation from live provider/Qdrant/ranking quality checks. | closed |
| T-04-02-01 | Tampering | `tests/fixtures/smoke_queries.json` | mitigate | Fixture stores category, request, min result count, must-have paths, banned fields, and top-N formula anchors; no exact raw score snapshots are frozen. | closed |
| T-04-02-02 | Safety/Misuse | `tests/test_smoke_queries.py` | mitigate | Smoke tests recursively ban generated medical-decision keys and require evidence/contraindication paths in responses. | closed |
| T-04-02-03 | Information Disclosure | `scripts/search_latency.py` live mode | mitigate | Live mode is opt-in through `--mode live --base-url`; default offline mode sends no patient text to network services. | closed |
| T-04-02-04 | Repudiation | latency JSON | mitigate | Report includes mode, query count, sample count, warmups, thresholds, threshold pass/fail, dataset size, index version, and metadata version. | closed |
| T-04-02-05 | Denial of Service | latency harness | mitigate | Defaults are bounded (`--runs 20`, `--warmups 3`), fixture TopK is validated, and the script is not a concurrent load generator. | closed |
| T-04-02-06 | Safety/Misuse | P50/P95 interpretation | mitigate | Verification states latency measures indexed search only and excludes import/index/corpus embedding; timing is not presented as medical correctness. | closed |

*Status: open / closed*
*Disposition: mitigate (implementation required) / accept (documented risk) / transfer (third-party)*

---

## Evidence Checked

| Evidence | Verified Behavior |
|----------|-------------------|
| `tests/test_quality_regression_contract.py` | Cross-cutting workbook-to-query-to-response coverage, sanitized provider failures, stale-index gating, and recursive banned medical-decision key checks. |
| `tests/fixtures/smoke_queries.json` | Seven structured smoke cases cover symptom, tongue, pulse, formula, article/source, and broad/sparse query paths without exact score snapshots. |
| `tests/test_smoke_queries.py` | Every fixture request validates through `PatientSearchRequest`, runs deterministic offline search, asserts evidence visibility, formula anchors, warnings, and banned-key absence. |
| `scripts/search_latency.py` | Offline default, explicit live `/api/search` mode, bounded runs/warmups, compact JSON report, and optional threshold enforcement. |
| `.planning/phases/04-quality-safety-and-performance-validation/04-VERIFICATION.md` | Documents repository verification as complete while keeping live latency and domain ranking review as human-required checks. |
| `.planning/phases/04-quality-safety-and-performance-validation/04-HUMAN-UAT.md` | Tracks pending live provider/runtime latency and doctor/customer ranking review. |

---

## Accepted Risks Log

No accepted risks. Live provider/runtime latency and clinical ranking adequacy are not accepted risks; they are tracked as pending human UAT because they require a configured demo environment and domain review.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-16 | 12 | 12 | 0 | Codex / gsd-execute-phase |

Verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py tests/test_quality_regression_contract.py tests/test_smoke_queries.py -q
```

Result: `147 passed, 18 warnings`

Latency command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline
```

Result: `thresholds_passed: true`, P50 0.065 ms, P95 0.113 ms, max 0.406 ms

Lint command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts
```

Result: `All checks passed!`

Known warnings: FastAPI/Starlette `TestClient` deprecation, `jieba` `pkg_resources` deprecation, and Qdrant client compatibility warnings when no local Qdrant server is running. These are not Phase 4 security gaps.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-16
