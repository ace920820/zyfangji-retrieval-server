---
phase: 02
slug: index-lifecycle-and-status
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-15
updated: 2026-06-15
---

# Phase 02 - Validation Strategy

> Reconstructed Nyquist validation contract from completed Phase 2 plans, summaries, tests, and verification artifacts.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.0 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py -q` |
| **Full suite command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py -q` |
| **Estimated runtime** | ~4 seconds focused, ~8 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the focused Phase 2 command above.
- **After every plan wave:** Run the focused Phase 2 command above.
- **Before `/gsd-verify-work`:** Run the full suite command above.
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | IDX-01 | T-02-01 / local source | Indexing contracts consume local `KnowledgeEntry` records and do not require customer DB access. | unit | `pytest tests/test_embedding_provider.py tests/test_qdrant_indexing.py -q` | yes | green |
| 02-01-02 | 01 | 1 | IDX-04 | T-02-01 / provider boundary | Embedding generation is behind a swappable provider interface with provider/model/vector metadata. | unit | `pytest tests/test_embedding_provider.py -q` | yes | green |
| 02-01-03 | 01 | 1 | IDX-05 | T-02-01 / vector store | Dense vector payload writes validate shape before Qdrant upsert and preserve canonical metadata. | unit | `pytest tests/test_qdrant_indexing.py -q` | yes | green |
| 02-02-01 | 02 | 2 | IDX-06 | T-02-02 / local BM25 | BM25 artifacts are versioned and Chinese tokenization preserves project TCM terms. | unit | `pytest tests/test_bm25_indexing.py -q` | yes | green |
| 02-02-02 | 02 | 2 | IDX-02 | T-02-02 / activation gate | Rebuilds create new versions and activate only after vector/BM25/local counts validate. | integration | `pytest tests/test_index_lifecycle.py -q` | yes | green |
| 02-02-03 | 02 | 2 | STAT-04 | T-02-02 / failure visibility | Provider/vector/BM25 failures mark builds failed and keep the previous active index intact. | integration | `pytest tests/test_index_lifecycle.py tests/test_embedding_provider.py -q` | yes | green |
| 02-03-01 | 03 | 3 | IDX-03 | T-02-03 / status truth | Status output exposes readiness, active version, counts, provider identifiers, timestamps, and last error. | unit/integration | `pytest tests/test_status_api.py -q` | yes | green |
| 02-03-02 | 03 | 3 | STAT-01 | T-02-03 / read-only status | `/status` and `index-status` expose model/store/retrieval/reranker status fields without provider calls. | integration | `pytest tests/test_status_api.py -q` | yes | green |
| 02-03-03 | 03 | 3 | STAT-02 | T-02-03 / health checks | `/health/live` and `/health/ready` give deployment/Java-backend readiness semantics. | integration | `pytest tests/test_status_api.py -q` | yes | green |
| 02-03-04 | 03 | 3 | STAT-03 | T-02-03 / failure visibility | Latest failed rebuilds are visible through status output and readiness JSON details. | integration | `pytest tests/test_status_api.py -q` | yes | green |

*Status: pending / green / red / flaky*

---

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| IDX-01 | COVERED | `tests/test_index_lifecycle.py::test_lifecycle_rebuild_loads_entries_from_local_metadata_only` |
| IDX-02 | COVERED | `tests/test_index_lifecycle.py::test_lifecycle_successful_rebuild_validates_then_activates`; `tests/test_index_lifecycle.py::test_index_rebuild_cli_activate_sets_active_index` |
| IDX-03 | COVERED | `tests/test_status_api.py::test_index_status_service_reports_active_index_details`; `tests/test_status_api.py::test_status_endpoint_returns_index_status_fields` |
| IDX-04 | COVERED | `tests/test_embedding_provider.py::test_deterministic_embedding_provider_returns_stable_metadata_and_vectors`; `tests/test_embedding_provider.py::test_validate_embedding_batch_rejects_dimension_mismatch` |
| IDX-05 | COVERED | `tests/test_qdrant_indexing.py::test_build_qdrant_payload_preserves_canonical_entry_fields`; `tests/test_qdrant_indexing.py::test_upsert_entries_validates_shape_before_client_call` |
| IDX-06 | COVERED | `tests/test_bm25_indexing.py::test_tokenize_chinese_text_preserves_project_tcm_terms`; `tests/test_bm25_indexing.py::test_bm25_store_builds_versioned_index_with_metadata` |
| STAT-01 | COVERED | `tests/test_status_api.py::test_status_endpoint_returns_index_status_fields`; `tests/test_status_api.py::test_index_status_cli_outputs_json_for_ready_and_not_ready_states` |
| STAT-02 | COVERED | `tests/test_status_api.py::test_health_live_returns_ok_without_active_index`; `tests/test_status_api.py::test_health_ready_returns_200_when_active_index_is_consistent`; `tests/test_status_api.py::test_health_ready_returns_503_when_no_active_index` |
| STAT-03 | COVERED | `tests/test_status_api.py::test_index_status_service_reports_not_ready_and_latest_failure`; `tests/test_status_api.py::test_health_ready_returns_503_when_active_counts_are_inconsistent` |
| STAT-04 | COVERED | `tests/test_index_lifecycle.py::test_lifecycle_failures_mark_failed_and_keep_previous_active`; `tests/test_embedding_provider.py::test_validate_embedding_batch_rejects_count_mismatch` |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-06-15

| Metric | Count |
|--------|-------|
| Requirements audited | 10 |
| Gaps found | 0 |
| Resolved by generated tests | 0 |
| Already covered | 10 |
| Escalated | 0 |

Focused verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py -q
```

Result: `40 passed, 1 warning in 3.55s`

Known warning: FastAPI/Starlette emits a `StarletteDeprecationWarning` from `fastapi.testclient`; this is an upstream dependency warning and does not affect Phase 2 validation coverage.

---

## Validation Sign-Off

- [x] All tasks have automated verification
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-15
