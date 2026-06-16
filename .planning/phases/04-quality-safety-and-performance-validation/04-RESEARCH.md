# Phase 04: Quality, Safety, and Performance Validation - Research

**Researched:** 2026-06-16
**Domain:** regression validation, medical-safety boundaries, provider failure handling, and indexed-search latency for the FastAPI retrieval service
**Confidence:** HIGH for existing coverage and planner gaps; MEDIUM for live latency expectations until measured on the final demo host

## Summary

Phase 4 should be a validation hardening phase, not a broad reimplementation phase. Phases 1-3 already have approved Nyquist coverage for ingestion contracts, local persistence, index lifecycle, status/health, search schemas, recall/fusion/rerank orchestration, and API response projection. [VERIFIED: .planning/phases/01-local-data-contract-and-ingestion/01-VALIDATION.md] [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VALIDATION.md] [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VALIDATION.md]

The main planning gaps are cross-cutting regression fixtures, real TCM smoke queries, deterministic offline provider behavior, explicit safety assertions, provider/stale-index failure probes, and a repeatable latency measurement command for an already-indexed MVP dataset. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md]

**Primary recommendation:** implement `04-01` as focused automated tests and fixtures over existing contracts, then implement `04-02` as a checked-in smoke-query dataset plus an offline latency harness that can run without real BGE/Qdrant by default and mark live provider/Qdrant verification separately. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: tests/test_search_pipeline.py] [VERIFIED: tests/test_search_api.py]

## User Constraints

No Phase 4 `CONTEXT.md` exists, so there are no additional locked user decisions beyond roadmap, requirements, project, AGENTS.md, and the objective prompt. [VERIFIED: gsd init phase-op 04] [VERIFIED: .planning/ROADMAP.md] [VERIFIED: .planning/REQUIREMENTS.md]

## Project Constraints

- MVP is retrieval-only and must not become a chat, diagnostic, or autonomous prescribing system. [VERIFIED: AGENTS.md] [VERIFIED: .planning/PROJECT.md]
- MVP reads local Excel / local structured files and must not depend on customer MySQL. [VERIFIED: AGENTS.md] [VERIFIED: .planning/PROJECT.md]
- MVP search chain includes BM25, BGE-M3 vector recall, hybrid fusion, BGE-Reranker-v2-m3 rerank, and TopK formula results. [VERIFIED: AGENTS.md] [VERIFIED: .planning/ROADMAP.md]
- Java backend integration needs stable HTTP API and documentation; the retrieval service does not own frontend display or business formulary composition lookup. [VERIFIED: AGENTS.md] [VERIFIED: .planning/PROJECT.md]
- Scores are ranking/display signals and must not be represented as medical confidence. [VERIFIED: AGENTS.md] [VERIFIED: .planning/REQUIREMENTS.md]
- Results should preserve source evidence, contraindication, and western-medicine-priority fields for physician review. [VERIFIED: AGENTS.md] [VERIFIED: src/zyfangji_retrieval/search/evidence.py]
- Before direct repo edits, AGENTS.md says to start work through a GSD entry point; this research turn was initiated by the GSD phase research workflow and wrote only the requested planning artifact. [VERIFIED: AGENTS.md] [VERIFIED: objective prompt]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-01 | Automated tests for Excel parsing, canonical normalization, stable ID generation, retrieval-text construction, query construction, and response schema. | Most primitives are already covered; plan only missing cross-file guard tests and avoid duplicating the approved Phase 1-3 tests. [VERIFIED: .planning/phases/01-local-data-contract-and-ingestion/01-VALIDATION.md] [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VALIDATION.md] |
| QUAL-02 | Smoke/regression queries for common symptoms such as headache, fever, aversion to wind, no sweat, tongue, and pulse combinations. | No checked-in smoke query dataset or result-baseline harness exists yet. [VERIFIED: rg smoke/regression tests src .planning] |
| QUAL-03 | Foreground source evidence and contraindication fields in API/demo output. | API projection includes evidence fields, but Phase 4 should add safety-focused assertions that every smoke result exposes evidence and contraindication/prioritization fields when present. [VERIFIED: tests/test_search_api.py] [VERIFIED: src/zyfangji_retrieval/search/evidence.py] |
| QUAL-04 | Keep generated medical advice, autonomous diagnosis, and autonomous prescription recommendations out of v1 responses. | Existing score-semantics tests exclude confidence/probability/prescription-certainty fields; Phase 4 should add broader negative-field/string assertions for advice/diagnosis/prescribing language. [VERIFIED: tests/test_search_api.py] [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] |
| QUAL-05 | Indexed `/api/search` targets P50 < 500ms and P95 < 1s for the MVP 1000-2000 row dataset, excluding first-time import and embedding generation. | No latency harness exists yet; the planner should add a repeatable command that measures warm indexed search, separates offline deterministic and live provider modes, and reports P50/P95. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: rg latency/perf/benchmark tests src] |

## Current Coverage Baseline

| Area | Existing Coverage | Planner Takeaway |
|------|-------------------|------------------|
| Excel headers and row parsing | Real workbook header count, Excel row 3 header, row 4 first data row, header drift, blank row skipping. [VERIFIED: tests/test_excel_ingestion.py] | Do not add duplicate header tests; add one Phase 4 meta-test only if it checks that the real sample fixture remains usable for smoke validation. |
| Canonical normalization | Row mapping to `KnowledgeEntry`, all 22 raw columns, normalized `main_symptom`, formula raw, sparse source code handling. [VERIFIED: tests/test_excel_ingestion.py] | Existing coverage satisfies much of QUAL-01. |
| Stable IDs | `make_entry_id()` deterministic with `shl_` prefix and reimports preserve ID set. [VERIFIED: tests/test_domain_contracts.py] [VERIFIED: tests/test_local_persistence.py] | Avoid retesting all ID internals; use IDs in smoke baselines as stable regression anchors. |
| Retrieval text | Contract-order labeled sections and display-only evidence exclusion are tested. [VERIFIED: tests/test_domain_contracts.py] | Phase 4 can assert smoke fixtures rely on these labels instead of creating a second query format. |
| Query construction | Patient fields become labeled `主症`, `复合症`, `舌诊`, `脉象`, `证型` sections; sparse/broad warnings are tested. [VERIFIED: tests/test_search_contracts.py] [VERIFIED: src/zyfangji_retrieval/search/query.py] | Add smoke cases that use realistic combinations, not more unit tests for labels. |
| Response schema | Top-level response shape, `retrieval_score`, `score_type`, source, formula, evidence, signal scores, warnings, metadata, and score semantics are tested. [VERIFIED: tests/test_search_api.py] | Phase 4 should freeze an end-to-end JSON subset for smoke queries. |
| Provider failures | Missing BGE endpoint, embedding failure, vector-store failure, required reranker failure, optional reranker degraded mode, and lifecycle provider/build failures are tested. [VERIFIED: tests/test_search_api.py] [VERIFIED: tests/test_search_pipeline.py] [VERIFIED: tests/test_index_lifecycle.py] | Add one scenario matrix or checklist tying these to demo handoff; do not duplicate every fake-provider test. |
| Stale or missing index | Missing active index, inconsistent health counts, failed rebuild preserving previous active index, and missing metadata for recalled entry are tested. [VERIFIED: tests/test_status_api.py] [VERIFIED: tests/test_search_pipeline.py] [VERIFIED: tests/test_index_lifecycle.py] | Phase 4 should verify stale-index behavior at API/handoff level and document live manual steps. |
| Live quality review | Phase 3 verification still requires live active-index search and real broad/sparse query inspection. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md] | Fold this into Phase 4 UAT or manual live checklist. |

## Requirement-by-Requirement Planning Notes for QUAL-01..QUAL-05

### QUAL-01

Plan a single focused test file such as `tests/test_quality_regression_contract.py` that imports existing builders and asserts the full path from workbook row -> canonical entry -> retrieval text -> patient query -> response JSON remains coherent. [VERIFIED: tests/test_excel_ingestion.py] [VERIFIED: tests/test_domain_contracts.py] [VERIFIED: tests/test_search_api.py]

The planner should reference existing tests as coverage evidence in `04-VALIDATION.md` and add only missing cross-cutting assertions. [VERIFIED: .planning/phases/01-local-data-contract-and-ingestion/01-VALIDATION.md] [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VALIDATION.md]

### QUAL-02

Create a checked-in smoke query fixture, preferably JSON or YAML, with query IDs, structured request payloads, expected minimum result count, expected formula names or article/source anchors where stable, and safety fields that must be present. [VERIFIED: .planning/REQUIREMENTS.md] [ASSUMED: JSON is the lowest-friction fixture format for this Python-only test suite]

Use categories from the requirement: symptom, formula, article, tongue, and pulse. Include at least headache/`头痛`, fever/`发热`, aversion to wind/`恶风`, no sweat/`无汗`, tongue, and pulse combinations. [VERIFIED: .planning/REQUIREMENTS.md]

### QUAL-03

For every smoke result, assert the response foregrounds `source`, `formula_raw`, `formula_mentions`, `formula_mapping_status`, and `evidence`; when source data contains contraindication or western-medicine-priority text, assert those fields remain visible in `evidence`. [VERIFIED: tests/test_search_api.py] [VERIFIED: src/zyfangji_retrieval/search/evidence.py]

Do not move contraindications into generated prose; keep them as structured fields for the Java/front-end layer. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] [VERIFIED: AGENTS.md]

### QUAL-04

Add negative assertions over serialized API responses that ban autonomous output fields such as `diagnosis`, `diagnosis_probability`, `prescription`, `prescription_certainty`, `medical_advice`, `treatment_plan`, and `confidence`, except where `confidence` appears inside the required score-semantics explanatory sentence if the test scans raw strings. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] [VERIFIED: tests/test_search_api.py]

The response may return `formula_raw` and formula identifiers because the project is a retrieval/reference service; the unsafe boundary is generating or asserting a diagnosis/prescription decision. [VERIFIED: .planning/PROJECT.md] [VERIFIED: .planning/REQUIREMENTS.md]

### QUAL-05

Add a latency command or pytest marker that measures indexed search only. Exclude first-time Excel import, embedding generation for corpus documents, and index rebuild from the timing window. [VERIFIED: .planning/REQUIREMENTS.md]

Use two modes: an offline deterministic mode for CI/local repeatability and a live mode for final demo host validation with configured Qdrant, BGE-M3, and reranker. [VERIFIED: tests/test_embedding_provider.py] [VERIFIED: tests/test_search_api.py] [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md]

## Recommended Test/Fixture Architecture

### Files to Add

| File | Purpose | Notes |
|------|---------|-------|
| `tests/fixtures/smoke_queries.json` | Stable smoke/regression query definitions. | Keep payloads structured exactly like `PatientSearchRequest`. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] |
| `tests/test_quality_regression_contract.py` | Cross-cutting QUAL-01, QUAL-03, QUAL-04 assertions. | Reuse existing fake `SearchService` style or extract shared fixtures if duplication becomes painful. [VERIFIED: tests/test_search_api.py] |
| `tests/test_smoke_queries.py` | Offline smoke query runner and snapshot-style assertions. | Should not require real BGE/Qdrant by default. [VERIFIED: tests/test_search_pipeline.py] |
| `tests/test_provider_and_index_failures.py` or extension to `tests/test_search_pipeline.py` | Handoff-level provider/stale-index failure scenarios. | Prefer extending existing tests if changes are small. [VERIFIED: tests/test_search_pipeline.py] |
| `scripts/search_latency.py` or CLI subcommand `search-latency` | Repeatable P50/P95 measurement. | Script can print JSON for Phase 4 validation artifact. [ASSUMED: a script is lower-risk than adding a hard perf gate to normal pytest] |

### Fixture Principles

- Keep default tests offline and deterministic; real provider/Qdrant runs should be opt-in through environment variables or a CLI flag. [VERIFIED: tests/test_embedding_provider.py] [VERIFIED: tests/test_qdrant_indexing.py]
- Use stable `entry_id`, formula name, and source article anchors for smoke comparisons, but avoid exact score snapshots because BM25/vector/reranker scores may change with tokenization, provider, or model revisions. [VERIFIED: tests/test_domain_contracts.py] [VERIFIED: tests/test_search_api.py] [ASSUMED: rank/order is a more stable regression signal than raw cross-provider scores]
- Snapshot only durable response structure and top-N identifiers/formulas; store observed `retrieval_score` and `signal_scores` as diagnostic output, not hard equality requirements. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py]

## Smoke Query Dataset Design

Recommended JSON shape:

```json
[
  {
    "id": "symptom_headache",
    "category": "symptom",
    "request": {"main_symptom": "头痛", "topk": 5},
    "expect": {
      "min_results": 1,
      "must_include_any_formula": ["麻黄汤"],
      "must_have_fields": ["source", "formula_raw", "evidence.source_article"]
    }
  },
  {
    "id": "taiyang_cold_no_sweat_pulse",
    "category": "symptom_tongue_pulse",
    "request": {
      "main_symptom": "发热恶寒",
      "symptoms": ["头痛", "无汗"],
      "pulse": "脉浮紧",
      "topk": 5
    },
    "expect": {
      "min_results": 1,
      "must_include_any_formula": ["麻黄汤"],
      "must_have_fields": ["evidence.pulse", "evidence.contraindication"]
    }
  }
]
```

Use expected formulas cautiously: the first real workbook row maps `头痛` to `麻黄汤`, so `头痛` -> `麻黄汤` is a reasonable initial smoke anchor. [VERIFIED: tests/test_excel_ingestion.py] Broader combinations such as `发热恶寒` + `恶风` may produce legitimate multiple formula rankings, so tests should allow top-N inclusion rather than exact rank unless a domain reviewer approves the baseline. [ASSUMED]

Recommended minimum dataset:

| Query ID | Request Focus | Assertion Style |
|----------|---------------|-----------------|
| `symptom_headache` | `main_symptom="头痛"` | At least one result; top-N includes workbook-known formula anchor if deterministic fixture uses real row. [VERIFIED: tests/test_excel_ingestion.py] |
| `symptom_fever_aversion_wind` | `main_symptom="发热恶寒"`, `symptoms=["恶风"]` | Ranked results and no diagnostic certainty fields. [VERIFIED: .planning/REQUIREMENTS.md] |
| `symptom_no_sweat_pulse` | `symptoms=["无汗"]`, `pulse="脉浮紧"` | Evidence includes pulse/source fields when present. [VERIFIED: src/zyfangji_retrieval/search/evidence.py] |
| `tongue_pulse_combo` | `tongue` + `pulse` only | Query construction accepts non-symptom structured fields. [VERIFIED: src/zyfangji_retrieval/search/query.py] |
| `formula_mahuang` | Formula-style user text such as `main_symptom="麻黄汤"` if accepted as a smoke query | Use only as retrieval regression, not medical recommendation. [ASSUMED] |
| `article_reference` | `main_symptom` or `syndrome` plus article-like text if sample data supports it | Assert source/article visibility, not exact clinical correctness. [ASSUMED] |
| `broad_sparse` | `main_symptom="寒"` | Expect `query_too_sparse` and `query_broad` warnings. [VERIFIED: tests/test_search_contracts.py] |

## Latency Measurement Strategy

### What to Measure

Measure only warm indexed `POST /api/search` execution for an already-active index. The requirement explicitly excludes first-time import and embedding generation. [VERIFIED: .planning/REQUIREMENTS.md]

### Recommended Harness

Implement a command that:

1. Loads smoke queries from `tests/fixtures/smoke_queries.json`. [ASSUMED]
2. Warms the service with 3-5 untimed requests. [ASSUMED]
3. Runs each smoke query 20-50 times in a single process. [ASSUMED]
4. Records elapsed wall-clock milliseconds per request using `time.perf_counter()`. [ASSUMED]
5. Prints JSON with `count`, `p50_ms`, `p95_ms`, `max_ms`, `mode`, `index_version`, `metadata_version`, and `dataset_size`. [ASSUMED]
6. Fails only when explicitly run in gate mode, e.g. `--enforce-thresholds`; otherwise writes a report for human review. [ASSUMED]

### Thresholds

| Metric | Target | Scope |
|--------|--------|-------|
| P50 | `< 500ms` | Indexed `/api/search`, MVP 1000-2000 row dataset, excluding import and corpus embedding. [VERIFIED: .planning/REQUIREMENTS.md] |
| P95 | `< 1s` | Same scope. [VERIFIED: .planning/REQUIREMENTS.md] |

### Offline vs Live

| Mode | Uses | Purpose |
|------|------|---------|
| Offline deterministic | Fake/deterministic embedding, fake vector retriever or local deterministic pipeline, deterministic reranker. | CI-safe regression guard for Python overhead, response projection, and smoke query contract. [VERIFIED: tests/test_embedding_provider.py] [VERIFIED: tests/test_search_pipeline.py] |
| Live local | Active SQLite metadata, BM25 artifact, Qdrant, configured BGE-M3 endpoint, configured reranker. | Final demo-host latency and live provider failure verification. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md] |

Do not make the default test suite fail because Qdrant or external BGE endpoints are missing; Phase 3 deliberately uses fakes for repository-only checks and marks live provider/Qdrant behavior as human-needed. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md] [VERIFIED: tests/test_qdrant_indexing.py]

## Safety/Medical Boundary Assertions

Add assertions that serialized successful responses:

- Include `score_semantics` and preserve language that scores are not medical confidence, diagnosis probability, or prescription certainty. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] [VERIFIED: tests/test_search_api.py]
- Include structured `source`, `formula_raw`, `formula_mapping_status`, and `evidence` fields for results. [VERIFIED: tests/test_search_api.py]
- Include `evidence.contraindication` and `evidence.western_medicine_priority` when source records contain those values. [VERIFIED: src/zyfangji_retrieval/search/evidence.py]
- Do not include top-level or nested generated-decision fields such as `diagnosis_probability`, `prescription_certainty`, `medical_advice`, `autonomous_diagnosis`, or `treatment_plan`. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: tests/test_search_api.py]
- Do not call customer business formulary databases or invent formula codes; `formula_code` is nullable and derived from local formula mentions only. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-SECURITY.md] [VERIFIED: src/zyfangji_retrieval/search/evidence.py]

## Provider/Stale Index Failure Verification

Existing tests already cover many low-level failures:

| Failure | Existing Coverage | Phase 4 Action |
|---------|-------------------|----------------|
| Missing BGE endpoint | `/api/search` returns typed `embedding_provider_unavailable` while health/status remain callable. [VERIFIED: tests/test_search_api.py] | Add to handoff checklist and avoid duplicate low-level test unless assertion needs safety output shape. |
| Embedding provider failure | Search service maps failure to `embedding_provider_unavailable`. [VERIFIED: tests/test_search_pipeline.py] | Include in provider-failure scenario matrix. |
| Qdrant/vector-store failure | Search service maps failure to `vector_store_unavailable`. [VERIFIED: tests/test_search_pipeline.py] | Include API-level smoke if not already covered at route level. |
| Required reranker failure | Search service raises `reranker_unavailable`. [VERIFIED: tests/test_search_pipeline.py] | Add one API-level assertion if planner wants stable Java envelope coverage. |
| Optional reranker failure | Search returns fused results with `reranker_degraded` warning when `reranker_required=False`. [VERIFIED: tests/test_search_pipeline.py] | Include as degradation-mode smoke case if demo may use optional reranker. |
| No active index | Search service raises `index_not_ready` before recall. [VERIFIED: tests/test_search_pipeline.py] | Add route-level or manual readiness check before demo. |
| Inconsistent active counts | `/health/ready` returns 503. [VERIFIED: tests/test_status_api.py] | Include stale-index readiness check in validation doc. |
| Missing recalled metadata | Search service raises `index_not_ready` with missing entry detail. [VERIFIED: tests/test_search_pipeline.py] | Keep as existing coverage; no need to duplicate. |

Manual/live verification should include: stop Qdrant or point `ZYFANGJI_QDRANT_URL` to a bad endpoint, unset `ZYFANGJI_EMBEDDING_ENDPOINT_URL`, run search with missing active index, and inspect JSON error envelopes for stable code/message/details without patient-text leakage. [VERIFIED: tests/test_search_api.py] [VERIFIED: tests/test_search_pipeline.py] [ASSUMED: live environment can be safely reconfigured during demo-prep validation]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `uv` | Running pytest and project commands | Yes | `uv 0.10.4` | Use system Python only for inspection; project requires uv-managed Python 3.12. [VERIFIED: local command `uv --version`] |
| `python3` | Local shell runtime check | Yes, but not project-compatible | `Python 3.9.6` | Use `uv run` because `pyproject.toml` requires `>=3.12,<3.13`. [VERIFIED: local command `python3 --version`] [VERIFIED: pyproject.toml] |
| pytest | Validation suite | Project dev dependency | `9.1.0` pinned | Install via `uv sync --dev` if missing. [VERIFIED: pyproject.toml] |
| Qdrant | Live latency and live provider failure checks | Not probed as running in this research | Version not verified locally | Default Phase 4 automated tests should not require live Qdrant; mark live checks manual/opt-in. [VERIFIED: tests/test_qdrant_indexing.py] |
| BGE-M3 embedding endpoint | Live semantic search and live latency | Not configured in repository defaults | Provider-specific | Use deterministic/offline provider tests by default; live validation requires env configuration. [VERIFIED: src/zyfangji_retrieval/config.py] [VERIFIED: tests/test_search_api.py] |
| BGE reranker | Live rerank latency | Not configured as a guaranteed local service | `BAAI/bge-reranker-v2-m3` default model id | Use deterministic reranker for offline tests; live validation requires target-host benchmark. [VERIFIED: src/zyfangji_retrieval/config.py] [VERIFIED: tests/test_search_pipeline.py] |

**Missing dependencies with no fallback:** none for repository-only Phase 4 automated tests if the planner keeps live checks opt-in. [VERIFIED: tests/test_qdrant_indexing.py] [VERIFIED: tests/test_search_pipeline.py]

**Missing dependencies with fallback:** live Qdrant/BGE/reranker availability can fall back to deterministic/offline validation for CI, but final demo latency and ranking quality still require live/manual validation. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md]

## Validation Architecture

Nyquist validation is enabled because `.planning/config.json` has `"nyquist_validation": true`. [VERIFIED: .planning/config.json]

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.0 [VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml` [VERIFIED: pyproject.toml] |
| Existing full suite command | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py tests/test_embedding_provider.py tests/test_qdrant_indexing.py tests/test_bm25_indexing.py tests/test_index_lifecycle.py tests/test_status_api.py tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py -q` [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VALIDATION.md] |
| Recommended Phase 4 focused command | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_quality_regression_contract.py tests/test_smoke_queries.py tests/test_search_api.py tests/test_search_pipeline.py -q` [ASSUMED] |
| Recommended latency command | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline` [ASSUMED] |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| QUAL-01 | Cross-cutting ingestion/query/response contract remains coherent. | unit/contract | `pytest tests/test_quality_regression_contract.py -q` | No, Wave 0. [VERIFIED: find phase/test files] |
| QUAL-02 | Smoke query set returns ranked comparable results. | regression/smoke | `pytest tests/test_smoke_queries.py -q` | No, Wave 0. [VERIFIED: rg smoke/regression tests src] |
| QUAL-03 | Evidence and contraindication fields remain visible. | API/contract | `pytest tests/test_quality_regression_contract.py tests/test_search_api.py -q` | Partial existing, Wave 0 for safety-focused coverage. [VERIFIED: tests/test_search_api.py] |
| QUAL-04 | No generated medical advice, autonomous diagnosis, or autonomous prescribing fields. | safety/negative contract | `pytest tests/test_quality_regression_contract.py -q` | Partial existing, Wave 0 for broader negative assertions. [VERIFIED: tests/test_search_api.py] |
| QUAL-05 | Indexed search P50/P95 report generated and optionally enforced. | performance/manual-live plus offline smoke | `python scripts/search_latency.py ...` | No, Wave 0. [VERIFIED: rg latency/perf/benchmark tests src] |

### Sampling Rate

- **Per task commit:** run the Phase 4 focused pytest command. [ASSUMED]
- **Per wave merge:** run Phase 4 focused command plus existing full suite. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VALIDATION.md]
- **Phase gate:** run full suite, offline smoke query suite, and latency report command; live latency/provider checks may be manual if external services are not configured. [VERIFIED: .planning/REQUIREMENTS.md] [ASSUMED]

### Wave 0 Gaps

- [ ] `tests/fixtures/smoke_queries.json` - supports QUAL-02 and QUAL-05. [VERIFIED: rg smoke/regression tests src]
- [ ] `tests/test_quality_regression_contract.py` - supports QUAL-01, QUAL-03, QUAL-04. [ASSUMED]
- [ ] `tests/test_smoke_queries.py` - supports QUAL-02 and offline safety assertions. [ASSUMED]
- [ ] `scripts/search_latency.py` or equivalent CLI command - supports QUAL-05. [ASSUMED]
- [ ] Optional `04-HUMAN-UAT.md` checklist - carries live BGE/Qdrant/reranker and doctor-review checks from Phase 3 into Phase 4. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md]

## Threat Model Planning Notes

| Threat Pattern | STRIDE / Safety Category | Existing Mitigation | Phase 4 Validation Need |
|----------------|--------------------------|---------------------|-------------------------|
| Patient text leakage through provider/vector/reranker errors | Information Disclosure | Provider and vector/reranker errors are wrapped without patient text. [VERIFIED: tests/test_search_pipeline.py] | Add one serialized API error smoke assertion for provider/vector failure if not already covered at route level. |
| Stale or partial index presented as fresh results | Spoofing / Safety | Search requires active index fields and nonzero counts; readiness returns 503 for inconsistent counts. [VERIFIED: src/zyfangji_retrieval/search/service.py] [VERIFIED: tests/test_status_api.py] | Include stale-index scenario in validation checklist and API tests. |
| Retrieval scores interpreted as medical certainty | Safety/Misuse | `score_semantics` excludes medical confidence, diagnosis probability, and prescription certainty. [VERIFIED: src/zyfangji_retrieval/domain/search_models.py] | Add smoke response assertions that score semantics remain present. |
| Generated advice or autonomous prescribing added by scope creep | Safety/Misuse | v1 requirements exclude medical diagnosis and autonomous prescribing. [VERIFIED: .planning/REQUIREMENTS.md] | Add negative response-field assertions across smoke outputs. |
| Missing contraindication/source evidence in demo output | Safety/Misuse | Evidence projection maps contraindication and western-medicine-priority source fields. [VERIFIED: src/zyfangji_retrieval/search/evidence.py] | Assert these fields survive for fixture entries that contain them. |
| Latency regression from provider/reranker changes | Denial of Service / Availability | Request size, TopK, recall Top50, and rerank candidate bounds exist. [VERIFIED: tests/test_search_contracts.py] [VERIFIED: tests/test_search_pipeline.py] | Add P50/P95 harness and report thresholds. |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile math in latency report | Custom approximate percentile algorithm | Python standard library sorting and index calculation for small sample counts, or `statistics.quantiles` with documented method. [ASSUMED] | Sample size is small enough; avoid extra dependency. |
| Golden snapshots of full JSON | Brittle full-response snapshots including scores/timestamps | Field-level assertions plus top-N anchors. [ASSUMED] | Provider/model/tokenizer changes can alter scores without breaking API contract. |
| Live provider simulator inside unit tests | Test-only HTTP server that pretends to be BGE/Qdrant | Existing fake providers and opt-in live checks. [VERIFIED: tests/test_search_pipeline.py] | Keeps default suite fast and independent of external services. |
| Medical quality rubric invented in code | Automated clinical correctness scoring | Smoke anchors plus human/domain review checklist. [ASSUMED] | Ranking usefulness is domain-sensitive and should not be overclaimed. |

## Risks, Assumptions, and Planner Guidance

### Risks

- Live P50/P95 may fail if BGE-M3 or reranker provider latency dominates request time; the requirement excludes corpus embedding generation but not query embedding or reranking. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: src/zyfangji_retrieval/search/service.py]
- The current runtime default requires BGE-M3 endpoint configuration; missing endpoint produces a typed search failure. [VERIFIED: src/zyfangji_retrieval/config.py] [VERIFIED: tests/test_search_api.py]
- Exact ranking expectations may be unstable across deterministic vs live provider modes; hard-code only stable anchors after observing real sample data. [ASSUMED]
- Domain-valid smoke queries need physician/customer review to become quality gates rather than technical smoke checks. [ASSUMED]

### Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JSON is the lowest-friction smoke fixture format for this Python test suite. | QUAL-02, Smoke Query Dataset Design | Planner might prefer YAML/CSV; implementation still straightforward. |
| A2 | Rank/order and top-N inclusion are more stable regression signals than raw scores. | Recommended Test/Fixture Architecture | If exact scores are required, live model/provider changes will create brittle tests. |
| A3 | Broad TCM query combinations may legitimately return multiple formula rankings, so exact rank needs domain approval. | Smoke Query Dataset Design | Tests could either overfit or under-detect ranking regressions. |
| A4 | A standalone latency script is lower-risk than a hard pytest performance gate. | Recommended Test/Fixture Architecture | Planner may choose pytest marker instead; local variance can cause flaky CI. |
| A5 | Live environment can be safely reconfigured during demo-prep failure validation. | Provider/Stale Index Failure Verification | If not true, failure checks must use a staging copy only. |
| A6 | Physician/customer review is needed before smoke queries become clinical quality gates. | Risks | Without review, tests validate technical stability, not clinical correctness. |

### Planner Guidance

Plan `04-01` around automated safety and contract tests: add the fixture file, cross-cutting regression tests, safety negative assertions, and provider/stale-index failure matrix. [VERIFIED: .planning/ROADMAP.md]

Plan `04-02` around smoke/regression query execution and latency measurement: add the smoke runner, report format, offline mode, live/manual mode, and Phase 4 validation artifact entries for P50/P95. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: .planning/REQUIREMENTS.md]

Do not require external BGE/Qdrant for normal CI unless the user explicitly says the live environment is provisioned. [VERIFIED: .planning/phases/03-hybrid-search-and-rerank-api/03-VERIFICATION.md]

## Sources

### Primary

- `.planning/ROADMAP.md` - Phase 4 scope, plans, and success criteria. [VERIFIED]
- `.planning/REQUIREMENTS.md` - QUAL-01..QUAL-05 and v1 safety boundaries. [VERIFIED]
- `.planning/PROJECT.md` and `AGENTS.md` - project constraints and workflow guidance. [VERIFIED]
- Phase 1-3 validation/security/verification artifacts - existing coverage baseline and live-human gaps. [VERIFIED]
- `pyproject.toml` - Python/package/test configuration. [VERIFIED]
- `tests/test_*.py` files listed in the objective - current automated coverage. [VERIFIED]
- `src/zyfangji_retrieval/search/service.py`, `query.py`, `evidence.py`, `api/routes/search.py`, `domain/search_models.py`, `config.py` - implementation behavior relevant to Phase 4. [VERIFIED]

### Secondary

- Local command output from `gsd-tools init phase-op 04`, `uv --version`, `python3 --version`, and `rg` searches for safety/performance/smoke terms. [VERIFIED]

### Tertiary

- None. No web research was needed because this phase is codebase-specific validation planning over already-selected stack decisions. [VERIFIED: thinking-models-research.md guidance for codebase-only research]

## Metadata

**Confidence breakdown:**

- Current coverage baseline: HIGH - sourced from completed validation artifacts and concrete test files. [VERIFIED]
- Fixture/test architecture: MEDIUM-HIGH - based on existing pytest/FastAPI patterns, with some implementation-shape assumptions. [VERIFIED] [ASSUMED]
- Latency strategy: MEDIUM - thresholds are locked, but live hardware/provider latency is unmeasured. [VERIFIED: .planning/REQUIREMENTS.md]
- Safety assertions: HIGH - v1 boundaries and response models are explicit. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: src/zyfangji_retrieval/domain/search_models.py]

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 for codebase planning; live latency findings expire when provider, host, or dataset changes. [ASSUMED]

## RESEARCH COMPLETE
