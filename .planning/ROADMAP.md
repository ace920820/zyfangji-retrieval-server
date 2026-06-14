# Roadmap: 中医方剂检索系统

## Overview

This roadmap delivers a retrieval-only TCM formula service for Java-backend integration and a two-to-three-week customer demo. MVP uses local Excel / local structured files as the knowledge source because the customer's MySQL schema and access method are not yet available. Work starts with canonical ingestion, then builds Qdrant/BM25 indexing, implements the full BM25 + BGE-M3 + Hybrid Fusion + BGE-Reranker-v2-m3 retrieval pipeline, validates quality/performance, and packages documentation plus a runnable demo without adding a lightweight admin console, customer MySQL sync, chat, NER, or LLM generation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Local Data Contract and Ingestion** - Convert the real `伤寒论` workbook into stable, auditable local knowledge entries.
- [ ] **Phase 2: Index Lifecycle and Status** - Build Qdrant/BM25 indexes from local metadata and expose readiness/status.
- [ ] **Phase 3: Hybrid Search and Rerank API** - Expose the patient search endpoint with BM25, vector recall, fusion, rerank, and evidence-rich results.
- [ ] **Phase 4: Quality, Safety, and Performance Validation** - Lock in regression tests, score/safety boundaries, and MVP latency checks.
- [ ] **Phase 5: Documentation and Demo Delivery** - Package OpenAPI docs, integration examples, Docker Compose, and a minimal reviewer demo flow.

## Phase Details

### Phase 1: Local Data Contract and Ingestion
**Goal**: System can convert the real `伤寒论` Excel sample into stable local knowledge entries with preserved source evidence and deterministic IDs.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, ING-01, ING-02, ING-03, ING-04, ING-05
**Success Criteria** (what must be TRUE):
  1. Operator can import the real `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` file and see total, valid, skipped, warning, failure, indexed, and version counts.
  2. Every imported searchable row has a deterministic `entry_id` that does not depend on sparse Excel `编码` values.
  3. All 22 source columns, raw records, normalized records, and evidence fields remain auditable through local metadata storage.
  4. Rows with multi-formula or ambiguous `推荐方剂` content preserve raw text and expose structured formula mentions or `needs_review` status.
  5. `retrieval_text` is generated from the agreed core fields and can be rebuilt without a customer MySQL connection.
**Plans**: 3 plans

Plans:
- [ ] 01-01: Define canonical knowledge-entry, formula mapping, and retrieval-text contracts
- [ ] 01-02: Implement Excel ingestion, field mapping, and validation reports
- [ ] 01-03: Persist raw and normalized local metadata with deterministic IDs

### Phase 2: Index Lifecycle and Status
**Goal**: System can build, validate, activate, and inspect local Qdrant/BM25 indexes without relying on customer business databases.
**Depends on**: Phase 1
**Requirements**: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05, IDX-06, STAT-01, STAT-02, STAT-03, STAT-04
**Success Criteria** (what must be TRUE):
  1. Operator can run a full rebuild that creates a new index version and activates it only after validation succeeds.
  2. BGE-M3 embeddings are generated through a swappable provider boundary and written to Qdrant with payload metadata.
  3. BM25 lexical indexing works over Chinese tokenized retrieval text and exact TCM fields.
  4. Status and health endpoints expose readiness, active version, indexed count, model/provider identifiers, last build time, update time, and last error.
  5. Embedding-provider failures return clear errors and do not present stale or partial results as fresh matches.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement embedding provider, Qdrant repository, and vector payload indexing
- [ ] 02-02: Implement BM25 indexing and versioned rebuild/activation flow
- [ ] 02-03: Expose status, health/readiness, and import/rebuild failure visibility

### Phase 3: Hybrid Search and Rerank API
**Goal**: Java backend can submit patient presentation data and receive TopK ranked formula results produced by BM25 recall, vector recall, hybrid fusion, and BGE rerank.
**Depends on**: Phase 2
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-07, PIPE-08, RES-01, RES-02, RES-03, RES-04, RES-05
**Success Criteria** (what must be TRUE):
  1. Java backend can call a stateless search endpoint with main symptom, symptom list, tongue, pulse, syndrome, and bounded `topk`.
  2. Search performs BM25 Top50 recall, BGE-M3 Qdrant Top50 recall, RRF or weighted hybrid fusion, and BGE-Reranker-v2-m3 reranking before returning results.
  3. Search response returns Top10 by default with rank, retrieval score, `score_type`, `entry_id`, source metadata, formula fields, and mapping status.
  4. Each result includes doctor-facing evidence fields such as symptoms, aliases, tongue, pulse, source article, syndrome, disease name, treatment method, contraindications, and efficacy assessment when present.
  5. Broad or sparse queries return ranked results and optional query-quality warnings without presenting scores as medical confidence.
**Plans**: 3 plans

Plans:
- [ ] 03-01: Define and expose patient search request, result, error, and score semantics schemas
- [ ] 03-02: Implement BM25/vector recall, hybrid fusion, and BGE rerank pipeline
- [ ] 03-03: Implement evidence projection, broad-query handling, and Java-friendly response contracts

### Phase 4: Quality, Safety, and Performance Validation
**Goal**: System behavior is regression-tested against real TCM query patterns, v1 safety boundaries, provider failures, and MVP latency expectations.
**Depends on**: Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05
**Success Criteria** (what must be TRUE):
  1. Automated tests cover Excel parsing, canonical normalization, stable ID generation, retrieval-text construction, query construction, and response schema.
  2. Common symptom, formula, article, tongue, and pulse smoke queries return ranked results that can be compared across changes.
  3. Source evidence and contraindication fields are foregrounded in API/demo output, while generated medical advice and autonomous prescribing stay out of v1.
  4. Provider failure and stale-index failure modes are tested or manually verified before demo handoff.
  5. Indexed `/api/search` targets P50 < 500ms and P95 < 1s on the MVP 1000-2000 row dataset, excluding first-time import and embedding generation.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Add automated ingestion, contract, query, response, provider-failure, and safety tests
- [ ] 04-02: Add smoke/regression query set and MVP search-latency validation

### Phase 5: Documentation and Demo Delivery
**Goal**: Reviewers and the Java/backend/frontend team can run the service, inspect API contracts, import sample data, and execute search flows without shell-only tribal knowledge.
**Depends on**: Phase 4
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. Developer can open OpenAPI/Swagger docs covering import, search, status, and health endpoints.
  2. Developer can follow documented environment variables, BGE-M3/reranker configuration, startup steps, and Docker Compose commands to run the service.
  3. Java-backend integration examples show import/status/search request and response flows.
  4. Reviewer can follow a minimal demo flow or sample client to import the sample `伤寒论` data and run a symptom search.
  5. Documentation states local-file data assumptions, score semantics, formula-code mapping behavior, privacy-conscious logging, and out-of-scope admin/chat/NER behavior.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Publish OpenAPI docs, Java integration examples, and configuration/deployment documentation
- [ ] 05-02: Build minimal demo flow or sample client for sample-data import and symptom search
- [ ] 05-03: Package Docker Compose, smoke flow, and out-of-scope documentation
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local Data Contract and Ingestion | 0/3 | Not started | - |
| 2. Index Lifecycle and Status | 0/3 | Not started | - |
| 3. Hybrid Search and Rerank API | 0/3 | Not started | - |
| 4. Quality, Safety, and Performance Validation | 0/2 | Not started | - |
| 5. Documentation and Demo Delivery | 0/3 | Not started | - |
