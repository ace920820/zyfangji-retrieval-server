# Requirements: 中医方剂检索系统

**Defined:** 2026-06-14
**Core Value:** 医生输入患者症状后，系统必须能稳定返回有典籍依据、排序合理、可回连业务方剂库的推荐方剂列表。

## v1 Requirements

Requirements for the MVP retrieval-service demo and Java-backend integration. MVP uses local Excel / local structured files as the knowledge source and does not depend on the customer's MySQL schema.

### Data Contract

- [x] **DATA-01**: System defines a canonical knowledge-entry schema that separates internal `entry_id`, source `编码`, source reference, formula name, formula code, raw formula text, mapping status, and raw source record.
- [x] **DATA-02**: System preserves all 22 source columns from the `伤寒论` Excel sample as retrievable/displayable metadata.
- [x] **DATA-03**: System generates deterministic stable `entry_id` values for imported rows without relying on sparse Excel `编码` values.
- [x] **DATA-04**: System represents multi-formula or multi-syndrome `推荐方剂` rows without hiding ambiguity, using raw text plus structured formula mentions or `needs_review` status.
- [x] **DATA-05**: System distinguishes core searchable fields from display-only evidence fields so noisy long-form text does not dominate retrieval.
- [x] **DATA-06**: System defines `retrieval_text` using main part, sub part, main symptom, complex symptom, detail symptom, alias, tongue, pulse, and syndrome fields.

### Local Ingestion

- [x] **ING-01**: System imports the real `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` workbook and skips title/header rows correctly.
- [x] **ING-02**: System reports total row count, valid row count, skipped row count, warning count, failed row details, indexed count, and index version after import.
- [x] **ING-03**: System validates required fields for searchable entries, including symptoms, formula text, source reference or source metadata, and evidence fields.
- [x] **ING-04**: System stores raw source records and normalized records in local metadata storage such as SQLite or JSONL so search results can be audited back to original rows.
- [x] **ING-05**: System can rebuild indexes from local metadata without requiring a customer MySQL connection.

### Indexing

- [x] **IDX-01**: System builds an independent retrieval index from normalized local knowledge entries rather than searching a customer business database directly.
- [x] **IDX-02**: System supports a full index rebuild that creates a new index version and activates it only after build validation succeeds.
- [x] **IDX-03**: System exposes index/status data including readiness, active version, indexed count, model/provider identifiers, last build time, and last error.
- [x] **IDX-04**: System supports BGE-M3 semantic embeddings through a swappable embedding-provider interface.
- [x] **IDX-05**: System writes dense vectors and payload metadata to Qdrant for vector recall.
- [x] **IDX-06**: System supports BM25-style lexical retrieval with Chinese tokenization for exact symptoms, aliases, formula names, tongue/pulse terms, and article references.

### Retrieval Pipeline

- [ ] **PIPE-01**: System exposes a stateless search endpoint for patient presentation data, including main symptom, symptom list, tongue, pulse, syndrome, and `topk`.
- [ ] **PIPE-02**: System constructs a normalized query text from structured patient fields using field labels and weighting-friendly structure.
- [ ] **PIPE-03**: System performs BM25 keyword recall and returns up to Top50 candidates.
- [ ] **PIPE-04**: System performs BGE-M3 vector recall from Qdrant and returns up to Top50 candidates.
- [ ] **PIPE-05**: System fuses BM25 and vector candidates using RRF or a configurable weighted score strategy.
- [ ] **PIPE-06**: System reranks the fused Top50 candidates using BGE-Reranker-v2-m3.
- [ ] **PIPE-07**: System returns Top10 by default and supports caller-provided `topk` within safe bounds.
- [ ] **PIPE-08**: System handles sparse or broad queries gracefully by returning a ranked list and optional query-quality warning rather than fabricating certainty.

### Result Contract

- [ ] **RES-01**: Each search result includes rank, retrieval score, `score_type`, `entry_id`, source metadata, formula raw text, formula mentions, formula code when known, and mapping status.
- [ ] **RES-02**: Each search result includes evidence fields needed by doctors: main symptom, compound symptoms, detailed symptoms, aliases, tongue, pulse, source article, syndrome, disease name, treatment method, contraindications, and efficacy assessment when present.
- [ ] **RES-03**: API documentation states that retrieval scores are ranking/reference signals, not medical confidence, diagnosis probability, or prescription certainty.
- [ ] **RES-04**: Search responses are designed for Java backend consumption and do not require the retrieval service to fetch prescription composition from a business formulary database.
- [ ] **RES-05**: Error responses use stable JSON shapes with machine-readable codes and human-readable messages.

### Status and Operations

- [x] **STAT-01**: System exposes a lightweight status endpoint with embedding model, reranker model, vector store, retrieval strategy, knowledge count, index version, and update time.
- [x] **STAT-02**: System exposes a health/readiness endpoint suitable for deployment and Java-backend integration checks.
- [x] **STAT-03**: Import and rebuild failures are visible through API responses or status output instead of failing silently.
- [x] **STAT-04**: Embedding or reranker provider failures return clear errors and do not present stale or partial results as fresh matches.

### Documentation and Deployment

- [ ] **DOC-01**: System publishes OpenAPI/Swagger documentation for import, search, status, and health endpoints.
- [ ] **DOC-02**: System includes Java-backend integration examples for import/status/search flows.
- [ ] **DOC-03**: System documents required environment variables, BGE-M3 / reranker provider configuration, startup steps, and Docker Compose commands.
- [ ] **DOC-04**: System documents local-file data assumptions, score semantics, formula-code mapping behavior, and out-of-scope medical-chat behavior.
- [ ] **DOC-05**: System provides a minimal demo flow or sample client where a reviewer can import the sample data and run a symptom search.

### Quality, Safety, and Performance

- [ ] **QUAL-01**: System includes automated tests for Excel parsing, canonical normalization, stable ID generation, retrieval-text construction, query construction, and response schema.
- [ ] **QUAL-02**: System includes smoke or regression queries for common sample symptoms such as headache, fever, aversion to wind, no sweat, tongue, and pulse combinations.
- [ ] **QUAL-03**: System foregrounds source evidence and contraindication fields in API/demo output to support physician review.
- [ ] **QUAL-04**: System keeps generated medical advice, autonomous diagnosis, and autonomous prescription recommendations out of v1 responses.
- [ ] **QUAL-05**: System targets indexed-search latency of P50 < 500ms and P95 < 1s for the MVP 1000-2000 row dataset, excluding first-time import and embedding generation.

## v2 Requirements

Deferred to future releases. Tracked but not in current v1 roadmap.

### Customer Data Integration

- **SYNC-01**: System can pull knowledge records from customer MySQL after schema, access method, and sync rules are confirmed.
- **SYNC-02**: System can run manual, scheduled, or incremental sync from customer business systems.
- **SYNC-03**: System can update retrieval indexes after upstream data changes.

### Lightweight Admin Console

- **ADMIN-01**: System can provide a lightweight admin UI for viewing knowledge libraries, row counts, import history, warnings, and failed rows.
- **ADMIN-02**: System can provide admin actions for uploading, deleting, and rebuilding a knowledge library.
- **ADMIN-03**: System can provide Qdrant/vector index inspection, including collection name, model, dimensions, vector count, and update time.
- **ADMIN-04**: System can delete by code, delete by book, delete all, re-embed, rebuild Qdrant, and rebuild BM25 from an operator UI.

### Conversational Features

- **CHAT-01**: System can ask follow-up questions when patient input is too broad or ambiguous.
- **CHAT-02**: System can generate natural-language explanations grounded only in retrieved source evidence.
- **CHAT-03**: System can support a full physician-facing chat UI if product scope and safety review approve it.

### NLP Features

- **NLP-01**: System can standardize symptoms such as `头疼 -> 头痛`, `发烧 -> 发热`, and `怕风 -> 恶风` using `同症异名` and a maintained alias table.
- **NLP-02**: System can extract symptoms, tongue, pulse, and syndrome fields from free-form clinical text using medical NER.

### Model Deployment

- **MODEL-01**: System can run private/local embedding, rerank, or language models when customer security or deployment requirements justify the cost.
- **MODEL-02**: System can compare provider quality, latency, and cost across public Chinese-capable embedding and rerank models.

### Multi-Source Expansion

- **MSRC-01**: System can import multiple non-`伤寒论` source books through configurable source adapters.
- **MSRC-02**: System can detect schema drift across customer-provided classics and generate mapping reports.
- **MSRC-03**: System can filter and rank results by source book, dataset version, and source reliability metadata.

## Out of Scope

Explicitly excluded from v1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Customer MySQL direct access or sync | Customer has not provided schema, access method, or sync rules; MVP validates retrieval from local files first. |
| Lightweight admin console | Moved to post-MVP so the first delivery stays focused on retrieval quality and API integration. |
| Generative TCM chatbot | Stakeholder discussion explicitly moved chat out of phase one; retrieval must be validated first. |
| Private LLM deployment | Too much infrastructure and operations work for a two-to-three-week demo; public or configured model APIs are acceptable for v1. |
| Symptom standardization and medical NER | Useful later, but MVP expects structured query fields and does not parse free-form medical text. |
| Automatic raw classical-text extraction | Customer currently provides curated structured tables; extraction requires separate domain QA. |
| Patient account/history workflow | Java business system owns users, visits, and patient records. |
| Prescription composition database | Retrieval service returns formula identifiers and evidence; business backend owns formula-drug details. |
| Medical diagnosis or autonomous prescribing | The system is physician reference retrieval, not a decision-making substitute. |
| Full production security/compliance certification | v1 demo needs safe defaults and privacy-conscious logging, but formal compliance review is a later workstream. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Verified |
| DATA-02 | Phase 1 | Verified |
| DATA-03 | Phase 1 | Verified |
| DATA-04 | Phase 1 | Verified |
| DATA-05 | Phase 1 | Verified |
| DATA-06 | Phase 1 | Verified |
| ING-01 | Phase 1 | Verified |
| ING-02 | Phase 1 | Verified |
| ING-03 | Phase 1 | Verified |
| ING-04 | Phase 1 | Verified |
| ING-05 | Phase 1 | Verified |
| IDX-01 | Phase 2 | Verified |
| IDX-02 | Phase 2 | Verified |
| IDX-03 | Phase 2 | Verified |
| IDX-04 | Phase 2 | Verified |
| IDX-05 | Phase 2 | Verified |
| IDX-06 | Phase 2 | Verified |
| PIPE-01 | Phase 3 | Pending |
| PIPE-02 | Phase 3 | Pending |
| PIPE-03 | Phase 3 | Pending |
| PIPE-04 | Phase 3 | Pending |
| PIPE-05 | Phase 3 | Pending |
| PIPE-06 | Phase 3 | Pending |
| PIPE-07 | Phase 3 | Pending |
| PIPE-08 | Phase 3 | Pending |
| RES-01 | Phase 3 | Pending |
| RES-02 | Phase 3 | Pending |
| RES-03 | Phase 3 | Pending |
| RES-04 | Phase 3 | Pending |
| RES-05 | Phase 3 | Pending |
| STAT-01 | Phase 2 | Verified |
| STAT-02 | Phase 2 | Verified |
| STAT-03 | Phase 2 | Verified |
| STAT-04 | Phase 2 | Verified |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Pending |
| DOC-04 | Phase 5 | Pending |
| DOC-05 | Phase 5 | Pending |
| QUAL-01 | Phase 4 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 4 | Pending |
| QUAL-04 | Phase 4 | Pending |
| QUAL-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

**Phase Coverage Summary:**
- Phase 1: 11 requirements (DATA-01..DATA-06, ING-01..ING-05)
- Phase 2: 10 requirements (IDX-01..IDX-06, STAT-01..STAT-04)
- Phase 3: 13 requirements (PIPE-01..PIPE-08, RES-01..RES-05)
- Phase 4: 5 requirements (QUAL-01..QUAL-05)
- Phase 5: 5 requirements (DOC-01..DOC-05)

---
*Requirements defined: 2026-06-14*
*Last updated: 2026-06-14 after Phase 2 verification*
