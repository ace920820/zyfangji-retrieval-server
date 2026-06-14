---
phase: 03
slug: hybrid-search-and-rerank-api
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-15
updated: 2026-06-15
---

# Phase 03 - Validation Strategy

> Reconstructed Nyquist validation contract from completed Phase 3 plans, summaries, tests, verification, and review artifacts.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.0 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q` |
| **Full suite command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py -q` |
| **Estimated runtime** | ~2 seconds focused, ~13 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the focused Phase 3 command above.
- **After every plan wave:** Run the focused Phase 3 command above.
- **Before `/gsd-verify-work`:** Run the full suite command above.
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | PIPE-01 / PIPE-07 / RES-03 / RES-05 | T-03-01 / search endpoint | Request fields are bounded, TopK defaults to 10 and rejects >50, scores are ranking signals only, and validation uses a stable envelope. | unit/contract | `pytest tests/test_search_contracts.py -q` | yes | green |
| 03-01-02 | 01 | 1 | PIPE-02 / PIPE-08 | T-03-01 / query normalization | Structured patient fields become labeled query text and sparse/broad warnings remain non-diagnostic. | unit | `pytest tests/test_search_contracts.py -q` | yes | green |
| 03-01-03 | 01 | 1 | PIPE-01 / RES-05 | T-03-01 / FastAPI boundary | `POST /api/search` is registered and service/validation failures use Java-friendly error envelopes. | API contract | `pytest tests/test_search_contracts.py tests/test_status_api.py -q` | yes | green |
| 03-02-01 | 02 | 2 | PIPE-03 / PIPE-04 | T-03-02 / provider and vector store | BM25 loads the active artifact, BGE-M3 provider is explicit, Qdrant uses the active collection, and provider/vector failures do not leak patient text. | unit/integration | `pytest tests/test_search_pipeline.py -q` | yes | green |
| 03-02-02 | 02 | 2 | PIPE-05 / PIPE-06 | T-03-02 / ranking providers | Fusion preserves signal ranks/scores and BGE reranker construction/failure handling is typed. | unit | `pytest tests/test_search_pipeline.py -q` | yes | green |
| 03-02-03 | 02 | 2 | PIPE-03 / PIPE-04 / PIPE-05 / PIPE-06 / PIPE-08 | T-03-02 / orchestration | SearchService requires an active index, runs recall/fusion/rerank in order, and emits typed degraded/error states. | service integration | `pytest tests/test_search_pipeline.py tests/test_search_contracts.py -q` | yes | green |
| 03-03-01 | 03 | 3 | RES-01 / RES-02 / RES-03 / RES-04 | T-03-03 / evidence projection | Response projection includes formula identity, source metadata, doctor-facing evidence, signal scores, and no business-formulary lookup. | API/service contract | `pytest tests/test_search_api.py tests/test_search_pipeline.py -q` | yes | green |
| 03-03-02 | 03 | 3 | PIPE-01 / PIPE-04 / PIPE-06 / RES-05 | T-03-03 / runtime wiring | App wiring is lazy, non-search endpoints survive missing BGE config, and provider/reranker choices are explicit. | API integration | `pytest tests/test_search_api.py tests/test_search_contracts.py tests/test_status_api.py -q` | yes | green |
| 03-03-03 | 03 | 3 | PIPE-07 / PIPE-08 / RES-01 / RES-03 / RES-05 | T-03-03 / Java response contract | Endpoint tests lock TopK, warnings, response keys, score semantics, and validation envelope shape. | API contract | `pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q` | yes | green |

*Status: pending / green / red / flaky*

---

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PIPE-01 | COVERED | `tests/test_search_contracts.py::test_search_route_is_registered`; `tests/test_search_contracts.py::test_search_route_calls_attached_search_service`; `tests/test_search_api.py::test_missing_bge_endpoint_keeps_health_status_callable_and_search_fails_typed` |
| PIPE-02 | COVERED | `tests/test_search_contracts.py::test_build_patient_query_uses_labeled_sections_and_separate_symptom_lines` |
| PIPE-03 | COVERED | `tests/test_search_pipeline.py::test_bm25_recall_loads_active_path_and_requests_top50`; `tests/test_search_pipeline.py::test_search_service_orchestrates_active_index_recall_fusion_and_rerank` |
| PIPE-04 | COVERED | `tests/test_search_pipeline.py::test_bge_m3_http_provider_parses_openai_compatible_response`; `tests/test_search_pipeline.py::test_vector_recall_embeds_query_and_uses_active_collection_top50`; `tests/test_search_pipeline.py::test_search_service_maps_vector_store_failure_to_typed_error` |
| PIPE-05 | COVERED | `tests/test_search_pipeline.py::test_rrf_fusion_preserves_signal_ranks_and_scores`; `tests/test_search_pipeline.py::test_fusion_rejects_unknown_strategy` |
| PIPE-06 | COVERED | `tests/test_search_pipeline.py::test_bge_reranker_provider_constructs_flag_reranker_and_sorts`; `tests/test_search_pipeline.py::test_search_service_required_reranker_failure_raises_typed_error` |
| PIPE-07 | COVERED | `tests/test_search_contracts.py::test_patient_search_request_defaults_topk_to_10`; `tests/test_search_api.py::test_search_route_defaults_topk_to_ten_and_returns_score_semantics`; `tests/test_search_api.py::test_search_route_rejects_topk_over_50_with_stable_validation_envelope` |
| PIPE-08 | COVERED | `tests/test_search_contracts.py::test_build_patient_query_emits_sparse_warning`; `tests/test_search_contracts.py::test_build_patient_query_emits_broad_warning_for_short_one_token_query`; `tests/test_search_pipeline.py::test_search_service_optional_reranker_failure_returns_degraded_fused_results` |
| RES-01 | COVERED | `tests/test_search_api.py::test_search_response_projects_java_friendly_evidence_shape`; `tests/test_search_api.py::test_formula_code_uses_first_non_empty_mention_code` |
| RES-02 | COVERED | `tests/test_search_api.py::test_search_response_projects_java_friendly_evidence_shape` |
| RES-03 | COVERED | `tests/test_search_contracts.py::test_search_response_documents_score_semantics`; `tests/test_search_api.py::test_search_route_defaults_topk_to_ten_and_returns_score_semantics` |
| RES-04 | COVERED | `tests/test_search_api.py::test_search_response_projects_java_friendly_evidence_shape`; `tests/test_search_api.py::test_formula_code_uses_first_non_empty_mention_code` |
| RES-05 | COVERED | `tests/test_search_contracts.py::test_search_route_validation_error_uses_stable_error_envelope`; `tests/test_search_contracts.py::test_search_route_returns_typed_service_error`; `tests/test_search_api.py::test_missing_bge_endpoint_keeps_health_status_callable_and_search_fails_typed` |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All Phase 3 requirement behaviors have automated verification. Live environment UAT remains tracked separately in `03-HUMAN-UAT.md` for configured Qdrant, BGE-M3 endpoint, BGE reranker, and real sample-ranking review.

---

## Validation Audit 2026-06-15

| Metric | Count |
|--------|-------|
| Requirements audited | 13 |
| Gaps found | 1 |
| Resolved by generated/updated tests | 1 |
| Already covered | 13 |
| Escalated | 0 |

Resolved gap:

- Updated `tests/test_embedding_provider.py::test_app_settings_exposes_index_defaults` to reflect the Phase 3 runtime default `embedding_provider="bge_m3"`, `embedding_model_id="BAAI/bge-m3"`, and `embedding_vector_size=1024`. This fixed a stale cross-phase test expectation from the earlier deterministic indexing phase.

Focused verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q
```

Result: `60 passed, 18 warnings in 1.45s`

Full-suite verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py -q
```

Result: `133 passed, 18 warnings in 12.78s`

Lint command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests
```

Result: `All checks passed!`

Known warnings: FastAPI/Starlette `TestClient` deprecation, `jieba` `pkg_resources` deprecation, and Qdrant client compatibility warnings when no local Qdrant server is running. These do not affect Phase 3 automated coverage.

---

## Validation Sign-Off

- [x] All tasks have automated verification
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-15
