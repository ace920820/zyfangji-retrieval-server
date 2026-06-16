---
phase: 03
slug: hybrid-search-and-rerank-api
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-16
updated: 2026-06-16
---

# Phase 03 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Java backend -> POST /api/search | Structured patient presentation data enters the retrieval service. | Patient symptoms, tongue, pulse, syndrome, and TopK. |
| FastAPI validation -> search dependency | Untrusted JSON is converted into typed models and either dispatched or rejected. | Validated `PatientSearchRequest` or stable validation error envelope. |
| OpenAPI/schema -> Java clients | Score and error semantics become external integration contracts. | Response, score semantics, and machine-readable error codes. |
| Search service -> SQLite index state | Search reads active resource pointers and must not mutate lifecycle records. | Active index version, metadata version, Qdrant collection, BM25 path, counts. |
| Search service -> Qdrant client | Query vector and active collection cross into vector store infrastructure. | BGE-M3 query vector, collection name, Qdrant payloads. |
| Search service -> embedding/reranker providers | Patient query text and candidate passages cross to model/provider boundaries. | Labeled patient query text and candidate retrieval text. |
| Search pipeline -> evidence projection | Internal candidate scores and source records become externally visible JSON. | Formula identity, source metadata, evidence fields, and diagnostic signal scores. |
| Search route -> error envelope | Internal failures cross to Java clients as stable machine-readable error codes. | Sanitized search-service error code, message, and details. |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-03-01-01 | Information Disclosure | `api/routes/search.py` | mitigate | No request-body logging exists in the route/search modules; provider/vector/reranker exceptions are wrapped into sanitized service errors. | closed |
| T-03-01-02 | Denial of Service | `PatientSearchRequest` | mitigate | Pydantic bounds enforce `topk=1..50`, max 20 symptoms, 200-char symptom items, and 500-char presentation fields. | closed |
| T-03-01-03 | Repudiation | error responses | mitigate | Validation and service failures return `SearchErrorEnvelope` with stable `error.code`, `error.message`, and `error.details`. | closed |
| T-03-01-04 | Safety/Misuse | score schema | mitigate | `SearchResponse.score_semantics` states retrieval scores are not medical confidence, diagnosis probability, or prescription certainty. | closed |
| T-03-01-05 | Tampering | route registration | mitigate | Phase 3 adds only the stateless `POST /api/search`; status tests verify no import/rebuild mutation endpoint was added. | closed |
| T-03-02-01 | Tampering | active index resolution | mitigate | SearchService reads active metadata from `SQLiteIndexStateStore.get_active()` and uses active `qdrant_collection`/`bm25_path`. | closed |
| T-03-02-02 | Denial of Service | recall/rerank pipeline | mitigate | `settings.recall_topk=50`, request `topk<=50`, fusion is limited to Top50, and reranker receives the bounded fused candidate list. | closed |
| T-03-02-03 | Information Disclosure | reranker/provider calls | mitigate | BGE-M3, Qdrant, and BGE reranker failures are wrapped without raw patient text or candidate evidence in outward errors. | closed |
| T-03-02-04 | Repudiation | provider/model outage behavior | mitigate | Required reranker failures raise `reranker_unavailable`; optional fallback emits `reranker_degraded` warning and pipeline status. | closed |
| T-03-02-05 | Spoofing | stale/partial index state | mitigate | SearchService rejects missing active index, missing resource pointers, zero counts, or missing metadata as `index_not_ready`. | closed |
| T-03-02-06 | Safety/Misuse | fused/rerank scores | mitigate | Signal scores remain diagnostic fields and confidence/probability/prescription-certainty semantics are explicitly excluded. | closed |
| T-03-03-01 | Information Disclosure | `api/routes/search.py` | mitigate | Route/service errors expose sanitized codes and details; no raw patient request body logging exists. | closed |
| T-03-03-02 | Safety/Misuse | response score fields | mitigate | Every `SearchResponse` carries score semantics; response models do not include `confidence`, `diagnosis_probability`, or `prescription_certainty` fields. | closed |
| T-03-03-03 | Repudiation | API error responses | mitigate | Known failures map to stable codes including `index_not_ready`, `vector_store_unavailable`, `embedding_provider_unavailable`, and `reranker_unavailable`; unknown search errors normalize to `search_internal_error`. | closed |
| T-03-03-04 | Denial of Service | `/api/search` | mitigate | Search preserves request TopK bounds, Top50 recall, Top50 fusion, and bounded reranker candidate flow. | closed |
| T-03-03-05 | Tampering | formula mapping | mitigate | Results return `formula_mapping_status` and nullable `formula_code` from local formula mentions only; no invented code or business formulary fetch is performed. | closed |
| T-03-03-06 | Spoofing | stale/partial index response | mitigate | Metadata includes `index_version` and `metadata_version`, and SearchService active-index checks gate result return. | closed |

*Status: open / closed*
*Disposition: mitigate (implementation required) / accept (documented risk) / transfer (third-party)*

---

## Evidence Checked

| Evidence | Verified Behavior |
|----------|-------------------|
| `src/zyfangji_retrieval/domain/search_models.py` | Request size bounds, score semantics, stable response/error schema, no medical confidence fields. |
| `src/zyfangji_retrieval/api/app.py` | Stable validation envelope, lazy search provider wiring, no request-body logging. |
| `src/zyfangji_retrieval/api/routes/search.py` | Search-service lookup, stable 503/500 envelopes, known code mapping, no raw request logging. |
| `src/zyfangji_retrieval/search/service.py` | Active index gating, Top50 recall/fusion, typed provider/vector/reranker/index errors, metadata versions in response. |
| `src/zyfangji_retrieval/search/embedding_factory.py` | BGE-M3 provider errors sanitized; deterministic provider only selected by explicit setting. |
| `src/zyfangji_retrieval/search/vector.py` | Qdrant calls use active collection and wrap vector-store failures. |
| `src/zyfangji_retrieval/search/rerank.py` | BGE reranker boundary wraps provider failures and sorts bounded candidates. |
| `src/zyfangji_retrieval/search/evidence.py` | Formula code comes from local mentions; formula mapping status and evidence fields are projected without business database fetch. |
| `tests/test_search_contracts.py` | Request bounds, score semantics, route registration, validation envelope, typed service error envelope. |
| `tests/test_search_pipeline.py` | BM25 Top50, Qdrant Top50, provider sanitization, RRF fusion, reranker behavior, active-index and provider failure handling. |
| `tests/test_search_api.py` | Java-friendly response shape, TopK behavior, warnings, lazy provider wiring, stable validation/provider errors. |
| `tests/test_status_api.py` | Route surface remains read/status/search only; no Phase 3 import/rebuild mutation route. |

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-16 | 17 | 17 | 0 | Codex / gsd-secure-phase |

Verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_api.py tests/test_search_pipeline.py tests/test_search_contracts.py tests/test_status_api.py -q
```

Result: `60 passed, 18 warnings in 2.36s`

Lint command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests
```

Result: `All checks passed!`

Known warnings: FastAPI/Starlette `TestClient` deprecation, `jieba` `pkg_resources` deprecation, and Qdrant client compatibility warnings when no local Qdrant server is running. These are not Phase 3 security gaps.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-16
