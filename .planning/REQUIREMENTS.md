# Requirements: 中医方剂检索系统

**Defined:** 2026-06-14
**Core Value:** 医生输入患者症状后，系统必须能稳定返回有典籍依据、排序合理、可回连业务方剂库的推荐方剂列表。

## v1 Requirements

Requirements for the initial retrieval-service demo and Java-backend integration.

### Data Contract

- [ ] **DATA-01**: System defines a canonical knowledge-entry schema that separates internal `entry_id`, source `编码`, source reference, formula name, formula code, raw formula text, and mapping status.
- [ ] **DATA-02**: System preserves all 22 source columns from the `伤寒论` Excel sample as retrievable/displayable metadata.
- [ ] **DATA-03**: System generates deterministic stable `entry_id` values for imported rows without relying on sparse Excel `编码` values.
- [ ] **DATA-04**: System represents multi-formula or multi-syndrome `推荐方剂` rows without hiding ambiguity, using raw text plus structured formula mentions or `needs_review` status.
- [ ] **DATA-05**: System distinguishes core searchable fields from display-only evidence fields so noisy long-form text does not dominate retrieval.

### Ingestion

- [ ] **ING-01**: System imports the real `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` workbook and skips title/header rows correctly.
- [ ] **ING-02**: System reports imported row count, valid row count, skipped row count, warning count, and failure details after import.
- [ ] **ING-03**: System validates required fields for searchable entries, including symptoms, formula text, source reference or source metadata, and evidence fields.
- [ ] **ING-04**: System supports importing canonical JSON rows from an upstream backend in addition to the local Excel sample path.
- [ ] **ING-05**: System stores raw source records and normalized records so search results can be audited back to the original source row.

### Indexing

- [ ] **IDX-01**: System builds an independent retrieval index from normalized knowledge entries rather than searching the business MySQL table directly.
- [ ] **IDX-02**: System supports a full index rebuild that creates a new index version and activates it only after build validation succeeds.
- [ ] **IDX-03**: System exposes index status including readiness, active version, indexed count, last build time, model/provider identifier, and last error.
- [ ] **IDX-04**: System supports dense semantic retrieval through a swappable embedding-provider interface.
- [ ] **IDX-05**: System supports lexical/BM25-style retrieval with Chinese tokenization for exact symptoms, aliases, formula names, tongue/pulse terms, and article references.
- [ ] **IDX-06**: System can add, update, or delete individual indexed data points by stable `entry_id`, even if implementation internally reindexes affected records.

### Search

- [ ] **SRCH-01**: System exposes a stateless search endpoint for patient presentation data, including symptoms, tongue diagnosis, pulse, inquiry notes, and supplemental description.
- [ ] **SRCH-02**: System accepts `top_k` with safe bounds and returns ranked results in descending retrieval relevance.
- [ ] **SRCH-03**: System constructs a normalized query text from structured patient fields using field labels and weighting-friendly structure.
- [ ] **SRCH-04**: System combines semantic and lexical signals for retrieval or exposes a baseline plus a clear path to hybrid fusion during quality tuning.
- [ ] **SRCH-05**: System returns matched-field diagnostics showing which source fields contributed to a result when available.
- [ ] **SRCH-06**: System handles sparse or broad queries gracefully by returning a ranked list and optional query-quality warning rather than fabricating certainty.

### Result Contract

- [ ] **RES-01**: Each search result includes rank, retrieval score, display score or score label, `entry_id`, source metadata, formula raw text, formula mentions, formula code when known, and mapping status.
- [ ] **RES-02**: Each search result includes evidence fields needed by doctors: main symptom, compound symptoms, detailed symptoms, aliases, tongue, pulse, source article, syndrome, disease name, treatment method, contraindications, and efficacy assessment when present.
- [ ] **RES-03**: API documentation states that retrieval scores are ranking/reference signals, not medical confidence, diagnosis probability, or prescription certainty.
- [ ] **RES-04**: Search responses are designed for Java backend consumption and do not require the retrieval service to fetch prescription composition from the business formulary database.
- [ ] **RES-05**: Error responses use stable JSON shapes with machine-readable codes and human-readable messages.

### Admin API

- [ ] **ADM-01**: System exposes health and readiness endpoints suitable for deployment and Java-backend integration checks.
- [ ] **ADM-02**: System exposes admin endpoints for import, rebuild, status, add/update, and delete operations.
- [ ] **ADM-03**: Long-running import/rebuild operations return job IDs and expose job status or completion details.
- [ ] **ADM-04**: Admin operations return validation warnings and failed-row details instead of silently accepting bad data.
- [ ] **ADM-05**: Admin API access can be protected or isolated for demo deployment so public users cannot mutate the index.

### Documentation

- [ ] **DOC-01**: System publishes OpenAPI/Swagger documentation for all search and admin endpoints.
- [ ] **DOC-02**: System includes Java-backend integration examples for import/rebuild/status/search flows.
- [ ] **DOC-03**: System documents required environment variables, embedding/rerank provider configuration, startup steps, and deployment commands.
- [ ] **DOC-04**: System documents data assumptions, score semantics, formula-code mapping behavior, and out-of-scope medical-chat behavior.

### Demo

- [ ] **DEMO-01**: System provides a minimal demo page or sample client where a reviewer can enter symptoms, tongue, pulse, notes, and topK.
- [ ] **DEMO-02**: Demo output shows formula, rank/score label, syndrome, treatment method, source evidence, contraindications, and mapping status for each result.
- [ ] **DEMO-03**: Demo environment can load the sample `伤寒论` data, rebuild the index, and run smoke queries without manual shell-only steps.
- [ ] **DEMO-04**: Demo deployment avoids logging patient-identifying free text beyond what is necessary for debugging.

### Quality and Safety

- [ ] **QUAL-01**: System includes automated tests for Excel parsing, canonical normalization, stable ID generation, query construction, and response schema.
- [ ] **QUAL-02**: System includes smoke or regression queries for common sample symptoms such as headache, fever, aversion to wind, no sweat, tongue, and pulse combinations.
- [ ] **QUAL-03**: System handles embedding-provider failures with clear errors and does not return stale or partial results as fresh matches.
- [ ] **QUAL-04**: System foregrounds source evidence and contraindication fields in API and demo output to support physician review.
- [ ] **QUAL-05**: System keeps generated medical advice, autonomous diagnosis, and autonomous prescription recommendations out of v1 responses.

## v2 Requirements

Deferred to future releases. Tracked but not in current v1 roadmap.

### Conversational Features

- **CHAT-01**: System can ask follow-up questions when patient input is too broad or ambiguous.
- **CHAT-02**: System can generate natural-language explanations grounded only in retrieved source evidence.
- **CHAT-03**: System can support a full physician-facing chat UI if product scope and safety review approve it.

### Model Deployment

- **MODEL-01**: System can run private/local embedding, rerank, or language models when customer security or deployment requirements justify the cost.
- **MODEL-02**: System can compare provider quality, latency, and cost across public Chinese-capable embedding and rerank models.

### Multi-Source Expansion

- **MSRC-01**: System can import multiple non-`伤寒论` source books through configurable source adapters.
- **MSRC-02**: System can detect schema drift across customer-provided classics and generate mapping reports.
- **MSRC-03**: System can filter and rank results by source book, dataset version, and source reliability metadata.

### Data Operations

- **OPS-01**: System can provide a richer admin UI for validation reports, ambiguous formula review, and formula-code mapping review.
- **OPS-02**: System can sync from customer MySQL on a schedule or webhook instead of manual import calls.

## Out of Scope

Explicitly excluded from v1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Generative TCM chatbot | Stakeholder discussion explicitly moved chat out of phase one; retrieval must be validated first. |
| Private LLM deployment | Too much infrastructure and operations work for a two-to-three-week demo; public model APIs are acceptable for v1. |
| Automatic raw classical-text extraction | Customer currently provides curated structured tables; extraction requires separate domain QA. |
| Patient account/history workflow | Java business system owns users, visits, and patient records. |
| Prescription composition database | Retrieval service returns formula identifiers and evidence; business backend owns formula-drug details. |
| Medical diagnosis or autonomous prescribing | The system is physician reference retrieval, not a decision-making substitute. |
| Full production security/compliance certification | v1 demo needs safe defaults and privacy-conscious logging, but formal compliance review is a later workstream. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| ING-01 | Phase 1 | Pending |
| ING-02 | Phase 1 | Pending |
| ING-03 | Phase 1 | Pending |
| ING-04 | Phase 1 | Pending |
| ING-05 | Phase 1 | Pending |
| IDX-01 | Phase 2 | Pending |
| IDX-02 | Phase 2 | Pending |
| IDX-03 | Phase 2 | Pending |
| IDX-04 | Phase 2 | Pending |
| IDX-05 | Phase 2 | Pending |
| IDX-06 | Phase 2 | Pending |
| SRCH-01 | Phase 3 | Pending |
| SRCH-02 | Phase 3 | Pending |
| SRCH-03 | Phase 3 | Pending |
| SRCH-04 | Phase 4 | Pending |
| SRCH-05 | Phase 3 | Pending |
| SRCH-06 | Phase 3 | Pending |
| RES-01 | Phase 3 | Pending |
| RES-02 | Phase 3 | Pending |
| RES-03 | Phase 3 | Pending |
| RES-04 | Phase 3 | Pending |
| RES-05 | Phase 3 | Pending |
| ADM-01 | Phase 2 | Pending |
| ADM-02 | Phase 2 | Pending |
| ADM-03 | Phase 2 | Pending |
| ADM-04 | Phase 2 | Pending |
| ADM-05 | Phase 2 | Pending |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Pending |
| DOC-04 | Phase 5 | Pending |
| DEMO-01 | Phase 5 | Pending |
| DEMO-02 | Phase 5 | Pending |
| DEMO-03 | Phase 5 | Pending |
| DEMO-04 | Phase 5 | Pending |
| QUAL-01 | Phase 4 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 2 | Pending |
| QUAL-04 | Phase 3 | Pending |
| QUAL-05 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

**Phase Coverage Summary:**
- Phase 1: 10 requirements (DATA-01..DATA-05, ING-01..ING-05)
- Phase 2: 12 requirements (IDX-01..IDX-06, ADM-01..ADM-05, QUAL-03)
- Phase 3: 12 requirements (SRCH-01, SRCH-02, SRCH-03, SRCH-05, SRCH-06, RES-01..RES-05, QUAL-04, QUAL-05)
- Phase 4: 3 requirements (SRCH-04, QUAL-01, QUAL-02)
- Phase 5: 8 requirements (DOC-01..DOC-04, DEMO-01..DEMO-04)

---
*Requirements defined: 2026-06-14*
*Last updated: 2026-06-14 after roadmap creation*
