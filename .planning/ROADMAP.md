# Roadmap: 中医方剂检索系统

## Overview

This roadmap delivers a retrieval-only TCM formula service for Java-backend integration and a two-to-three-week customer demo. Work starts with the data contract and canonical ingestion because stable IDs, preserved evidence, and formula mapping are prerequisites for every index, API response, and demo result. Later phases add independent index lifecycle management, Java-friendly search/result contracts, retrieval quality checks, and reproducible documentation/demo delivery without adding chat, generative diagnosis, private LLM deployment, or prescription composition joins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Contract and Canonical Ingestion** - Normalize the real `伤寒论` workbook into stable, auditable knowledge entries.
- [ ] **Phase 2: Index Lifecycle and Admin Operations** - Build and operate independent retrieval indexes through managed APIs.
- [ ] **Phase 3: Search API and Evidence Results** - Expose the patient search endpoint and evidence-rich Java-consumable response contract.
- [ ] **Phase 4: Retrieval Quality and Safety Validation** - Tune hybrid retrieval behavior and lock in regression, schema, and safety checks.
- [ ] **Phase 5: Documentation and Demo Delivery** - Package OpenAPI docs, integration examples, deployment steps, and a minimal reviewer demo.

## Phase Details

### Phase 1: Data Contract and Canonical Ingestion
**Goal**: System can convert the real `伤寒论` Excel sample and backend-pushed canonical rows into stable, auditable knowledge entries with preserved source evidence.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, ING-01, ING-02, ING-03, ING-04, ING-05
**Success Criteria** (what must be TRUE):
  1. Operator can import the real `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` file and see valid, skipped, warning, and failure counts.
  2. Every imported searchable row has a deterministic `entry_id` that does not depend on sparse Excel `编码` values.
  3. Searchable fields, display-only evidence fields, raw source records, normalized records, and all 22 source columns are available for audit.
  4. Rows with multi-formula or ambiguous `推荐方剂` content preserve raw text and expose structured formula mentions or `needs_review` status.
  5. Upstream canonical JSON rows can be accepted through the same knowledge-entry contract as Excel-derived rows.
**Plans**: 3 plans

Plans:
- [ ] 01-01: Define canonical knowledge-entry and formula mapping contracts
- [ ] 01-02: Implement Excel and canonical JSON ingestion with validation reports
- [ ] 01-03: Persist raw and normalized records with deterministic IDs and audit metadata

### Phase 2: Index Lifecycle and Admin Operations
**Goal**: System can build, inspect, rebuild, and mutate independent retrieval indexes without scanning the Java business database directly.
**Depends on**: Phase 1
**Requirements**: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05, IDX-06, ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Operator can run a full rebuild that creates a new index version and activates it only after validation succeeds.
  2. Java backend or operator can check health, readiness, active index version, indexed count, provider identifier, last build time, and last error.
  3. Admin client can import, rebuild, add, update, or delete data points by stable `entry_id` and receive job IDs for long-running operations.
  4. Dense semantic indexing and Chinese lexical/BM25-style indexing both work behind swappable provider or repository boundaries.
  5. Embedding-provider failures return clear errors and do not present stale or partial results as fresh matches.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement index repositories, embedding provider interface, and lexical tokenization
- [ ] 02-02: Implement rebuild/version activation and entry-level index mutation flows
- [ ] 02-03: Expose health, readiness, admin jobs, validation warnings, and protected admin operations

### Phase 3: Search API and Evidence Results
**Goal**: Java backend can submit patient presentation data and receive ranked, evidence-rich retrieval results without prescription composition joins.
**Depends on**: Phase 2
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-05, SRCH-06, RES-01, RES-02, RES-03, RES-04, RES-05, QUAL-04, QUAL-05
**Success Criteria** (what must be TRUE):
  1. Java backend can call a stateless search endpoint with symptoms, tongue, pulse, inquiry notes, supplemental description, and bounded `top_k`.
  2. Search response returns results in descending retrieval relevance with rank, retrieval score, display score or label, `entry_id`, source metadata, formula fields, and mapping status.
  3. Each result includes doctor-facing evidence fields such as symptoms, aliases, tongue, pulse, source article, syndrome, disease name, treatment method, contraindications, and efficacy assessment when present.
  4. Response diagnostics can show matched source fields when available and broad or sparse queries return ranked results with optional quality warnings.
  5. API errors use stable JSON codes/messages and response wording keeps scores as retrieval references, not medical confidence or autonomous prescription advice.
**Plans**: 3 plans

Plans:
- [ ] 03-01: Define and expose patient search request, result, error, and score semantics schemas
- [ ] 03-02: Implement normalized query construction and ranked evidence projection
- [ ] 03-03: Add matched-field diagnostics, sparse-query warnings, and safety framing in responses

### Phase 4: Retrieval Quality and Safety Validation
**Goal**: System behavior is regression-tested against real TCM query patterns, hybrid retrieval expectations, and v1 safety boundaries.
**Depends on**: Phase 3
**Requirements**: SRCH-04, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. Common symptom, formula, article, tongue, and pulse smoke queries return ranked results that can be compared across changes.
  2. Search can combine semantic and lexical signals or expose a tested baseline plus clear hybrid-fusion path for quality tuning.
  3. Automated tests cover Excel parsing, canonical normalization, stable ID generation, query construction, and response schema.
  4. Retrieval regressions, schema drift, and provider failure handling are caught before demo handoff.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Add automated contract, ingestion, query construction, response schema, and provider-failure tests
- [ ] 04-02: Add smoke/regression query set and hybrid retrieval quality tuning

### Phase 5: Documentation and Demo Delivery
**Goal**: Reviewers and the Java/backend/frontend team can run the demo, inspect API contracts, and integrate search flows without shell-only tribal knowledge.
**Depends on**: Phase 4
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DEMO-01, DEMO-02, DEMO-03, DEMO-04
**Success Criteria** (what must be TRUE):
  1. Developer can open OpenAPI/Swagger docs covering all search and admin endpoints with Java-backend flow examples.
  2. Developer can follow documented environment variables, provider configuration, startup steps, and deployment commands to run the service.
  3. Reviewer can use a minimal demo page or sample client to enter symptoms, tongue, pulse, notes, and topK, then inspect ranked evidence results.
  4. Demo environment can load the sample `伤寒论` data, rebuild the index, and run smoke queries without manual shell-only steps.
  5. Documentation and demo messaging state data assumptions, score semantics, formula-code mapping behavior, privacy-conscious logging, and out-of-scope chat behavior.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Publish OpenAPI docs, Java integration examples, and configuration/deployment documentation
- [ ] 05-02: Build minimal search demo page or sample client with evidence-first output
- [ ] 05-03: Package demo bootstrap, smoke flows, privacy-conscious logging, and out-of-scope documentation
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Contract and Canonical Ingestion | 0/3 | Not started | - |
| 2. Index Lifecycle and Admin Operations | 0/3 | Not started | - |
| 3. Search API and Evidence Results | 0/3 | Not started | - |
| 4. Retrieval Quality and Safety Validation | 0/2 | Not started | - |
| 5. Documentation and Demo Delivery | 0/3 | Not started | - |
