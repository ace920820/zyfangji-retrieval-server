# Project Research Summary

**Project:** 中医方剂检索系统
**Domain:** Physician-facing TCM formula retrieval API with structured classical-text data
**Researched:** 2026-06-14
**Confidence:** HIGH for v1 scope, data risks, and service architecture; MEDIUM for final embedding/reranker provider choice

## Executive Summary

中医方剂检索系统 should be built as a deterministic retrieval service for doctors and the Java business backend, not as a generative TCM chatbot. Experts would treat the current `伤寒论` workbook as structured knowledge, normalize it into stable canonical entries, build an independent retrieval index, and return ranked formula references with source evidence, contraindications, and business-linking identifiers. The Java system should continue to own users, patient workflow, prescription-library joins, and final UI display.

The recommended v1 approach is a Python FastAPI microservice using pandas/openpyxl for Excel ingestion, Qdrant for vector storage, `bm25s` + jieba for lexical matching, and an external Chinese-capable embedding API behind a provider interface. Start with reliable import, stable IDs, field-weighted indexed text, and a topK search API. Add hybrid score fusion as part of the first retrieval-quality benchmark; keep reranking optional until baseline results and latency are measured.

The critical risks are data-contract mistakes, not model selection. The current Excel `编码` column is mostly blank and cannot be the public identifier; `推荐方剂` often contains multiple formulas or clinical branches; raw similarity scores can be mistaken for medical confidence; and pure vector search can miss exact TCM terms. Mitigate these by separating `entry_id`, `source_ref`, and `formula_code`, producing import validation reports, preserving original evidence fields, labeling scores as retrieval relevance only, and validating exact-term queries before demo.

## Key Findings

### Recommended Stack

Build v1 as a small Python retrieval microservice with explicit ingestion, indexing, and search modules. Avoid LangChain/LlamaIndex as the core because the product is not a multi-step agent or chat workflow; it needs deterministic ranked rows, operational index management, and a stable OpenAPI contract for Java integration.

Use cloud/public embedding APIs for the 2-3 week demo unless customer policy blocks them. Keep provider choice swappable because account, region, compliance, and deployment constraints are still unresolved.

**Core technologies:**
- Python 3.12.x: service runtime — best ecosystem for embeddings, vector DB clients, Excel parsing, BM25, and reranking.
- FastAPI 0.136.3 + Pydantic 2.13.4 + Uvicorn 0.49.0: HTTP API — native OpenAPI docs, typed request/response schemas, easy Java backend integration.
- Qdrant 1.18.2 + qdrant-client 1.18.0: vector/search store — dense vectors, sparse/hybrid patterns, payload filters, upsert/delete, snapshots, and simple Docker deployment.
- pandas 3.0.3 + openpyxl 3.1.5: Excel ingestion — fastest reliable path for the real `.xlsx` sample.
- `bm25s` 0.3.9 + jieba 0.42.1: lexical retrieval — protects exact formula names, article numbers, tongue/pulse terms, aliases, and short Chinese medical phrases.
- pydantic-settings, httpx, Typer, pytest, ruff, Docker Compose: config, provider calls, maintenance CLI, tests, linting, and repeatable demo deployment.

### Expected Features

v1 must prove that real structured TCM data can be imported, indexed, searched, and returned through a Java-friendly contract. The demo should be evidence-first and physician-facing, not a full clinical workflow or patient app.

**Must have (table stakes):**
- Structured Excel import for the real `伤寒论` sample — preserve all display fields and report row counts, warnings, and failures.
- Stable `entry_id` generation — do not depend on Excel row numbers or sparse `编码` values.
- Formula normalization contract — return formula name, raw formula text, formula code when known, and mapping status when unresolved.
- Stateless search API — accept symptoms, tongue, pulse, notes, and `topK`; return ranked formula entries.
- Evidence-rich result schema — include source article/original text, syndrome, disease, treatment method, contraindications, and score/rank.
- Admin import/rebuild/status/update/delete APIs — operators and Java backend need to manage index state without shell scripts.
- OpenAPI documentation and examples — required for backend/frontend integration.
- Minimal demo page or sample client — enough to show query input, topK results, evidence, and index status within the 2-3 week window.
- Safe medical framing — responses are classical-reference retrieval for doctor review, not autonomous diagnosis or prescription.

**Should have (competitive):**
- Hybrid keyword + semantic retrieval — improves recall and trust for exact TCM terms and fuzzy symptom descriptions.
- Field-level match explanation — show which symptoms, tongue, pulse, syndrome, disease, or formula fields contributed.
- Query synonym expansion — start with `同症异名` and curated TCM dictionary terms.
- Dataset/source version awareness — prepare for expansion beyond `伤寒论`.
- Import validation report for formula splitting, missing codes, duplicate names, and ambiguous rows.

**Defer (v2+):**
- Generative TCM chat, follow-up questioning, or generated clinical explanations — changes scope, liability, and test burden.
- Private/local LLM deployment — costly and unnecessary for the v1 demo unless customer policy requires it.
- Automatic extraction from raw classical books — wait until curated table schemas and QA workflow are stable.
- Patient history, accounts, favorites, or full physician workflow — belongs in the business system unless product scope changes.
- Cross-book conflict resolution — defer until multiple classics are actually imported and conflicts are visible.

### Architecture Approach

Use one deployable FastAPI service with strong internal boundaries: API routes stay thin, domain models define stable contracts, ingestion normalizes source data, indexing owns vector/keyword state, search owns retrieval/ranking/projection, and persistence stores canonical records plus job/index metadata. Treat MySQL/business tables as upstream data, not the retrieval engine.

**Major components:**
1. API layer — exposes search, admin import/rebuild/update/delete, health, index status, and OpenAPI docs.
2. Import adapter + validator — reads Excel/CSV/JSON or Java-pushed rows, validates fields, and preserves raw source display fields.
3. Normalizer + ID/formula mapper — creates canonical `KnowledgeEntry` records, stable `entry_id`, `source_ref`, formula mentions, and mapping status.
4. Metadata repository — stores canonical records, import batches, job state, index versions, raw fields, and audit data.
5. Embedding provider + keyword encoder — converts entries and queries into dense vectors and lexical tokens behind swappable interfaces.
6. Index repository — the only boundary that mutates/searches Qdrant/BM25 index state.
7. Retriever + scorer/reranker — runs dense and lexical candidate retrieval, field boosts, optional reranking, and score diagnostics.
8. Result projector — returns formula references, evidence, contraindications, and source fields without fetching prescription composition from the Java system.
9. Index job orchestrator — builds staging index versions, validates them, and atomically activates the new version.

### Critical Pitfalls

1. **Treating Excel `编码` as a stable business identifier** — create separate `entry_id`, `source_ref`, and `formula_code`; return unresolved mapping status instead of fake codes.
2. **Failing to split multi-formula or multi-syndrome rows** — preserve original rows for audit, but normalize candidate entries by branch where possible and mark ambiguous cases as `needs_review`.
3. **Interpreting similarity scores as medical confidence** — label scores as retrieval relevance/ranking diagnostics, avoid percent-confidence UI, and foreground rank plus evidence.
4. **Building pure vector search only** — include BM25/keyword retrieval, jieba tokenization, TCM synonym dictionary, field weighting, and exact-term regression tests.
5. **Indexing all display text as clinical evidence** — separate retrieval-core fields from evidence/display fields and make constructed indexed text inspectable.
6. **Fragile demo operations** — expose import/rebuild/status APIs, data version, entry counts, model/provider state, failed rows, and smoke queries.
7. **Hardcoding one 22-column schema everywhere** — define canonical fields and source adapters now so future books do not force a rewrite.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Contract and Canonical Ingestion
**Rationale:** Stable identifiers, formula mapping, and field normalization are prerequisites for every API, index, and demo result. Data mistakes here are the highest-risk failure mode.
**Delivers:** Canonical `KnowledgeEntry` model, field manifest, Excel reader, validation report, deterministic `entry_id`, `source_ref`, formula name/code/mapping status, preserved raw display fields, and import fixtures.
**Addresses:** Structured Excel import, stable IDs, formula normalization contract, evidence preservation.
**Avoids:** Unstable IDs, noisy indexed fields, multi-formula ambiguity hidden inside one result, and hardcoded source-column leakage.

### Phase 2: Index Lifecycle and Baseline Retrieval
**Rationale:** Search quality can only be evaluated after real normalized entries can be indexed, rebuilt, inspected, and activated safely.
**Delivers:** Qdrant collection setup, embedding provider interface, BM25/jieba index, full rebuild, active index version, status endpoint, row-count validation, and initial topK search over real data.
**Uses:** FastAPI, Qdrant, qdrant-client, external embedding provider, `bm25s`, jieba, pandas/openpyxl.
**Implements:** Index repository, embedding provider, keyword encoder, retriever, and index job orchestrator.
**Avoids:** Pure vector search, stale hidden index state, in-place rebuild downtime, and shell-only demo rebuilds.

### Phase 3: Search API Contract, Scoring, and Evidence Projection
**Rationale:** Java integration and frontend display need a frozen response shape before UI polish or advanced ranking. Score semantics and safety language must be defined early.
**Delivers:** `/search/formulas` request/response schemas, topK bounds, rank/retrieval score diagnostics, evidence-rich result payload, contraindication fields, mapping status, OpenAPI examples, and error shapes.
**Addresses:** Search API, ranked results, match score semantics, evidence fields, Java backend contract.
**Avoids:** Score-as-medical-confidence, missing contraindications, ambiguous formula joins, and API churn.

### Phase 4: Hybrid Quality, Field Matching, and Evaluation Set
**Rationale:** After the contract and baseline retrieval exist, tune quality against real queries and exact-term expectations instead of guessing model behavior.
**Delivers:** Dense + BM25 fusion, field weights, exact formula/article/symptom/tongue/pulse regression queries, matched-field diagnostics, synonym expansion from `同症异名`, and optional reranker feature flag if needed.
**Addresses:** Hybrid retrieval, field-level match explanation, query synonym handling, broad-query diagnostics.
**Avoids:** Exact TCM terms being lost, over-trusting embeddings, ranking regressions after tuning, and unexplainable results.

### Phase 5: Admin Operations and Demo Hardening
**Rationale:** The customer demo must be reproducible and diagnosable, not a one-off local script. Admin operations should prove index maintenance expectations before handoff.
**Delivers:** Import/rebuild/update/delete endpoints, job IDs/status, health/readiness, provider-key startup checks, structured logs, safe error handling, smoke queries, Docker Compose deployment, and minimal demo page/sample client.
**Addresses:** Data maintenance endpoints, index status, health checks, observability, demo page, public credential configuration.
**Avoids:** Stale vectors, silent model/API failures, public admin exposure, patient-data logging, and deployment surprises.

### Phase 6: Multi-Source Expansion Readiness
**Rationale:** Expansion to up to 200 books is a separate product risk because future field consistency is not confirmed.
**Delivers:** Source adapter boundary, mapping config format, dataset/source metadata, validation report by source, and a trial import of at least one non-`伤寒论` representative file when available.
**Addresses:** Dataset/version-aware retrieval and future multi-book schema mapping.
**Avoids:** Rewriting retrieval logic for each book, inconsistent search quality across sources, and premature raw-text extraction.

### Phase Ordering Rationale

- Data contract comes first because `entry_id`, formula mapping, branch handling, and preserved evidence are dependencies for search, admin APIs, Java integration, and demo trust.
- Index lifecycle precedes quality tuning because model behavior cannot be judged on toy rows or unstable imports.
- API/scoring contract precedes UI hardening because Java and frontend teams need stable schemas and safe wording.
- Hybrid tuning follows baseline retrieval so field weights, synonyms, and reranking are driven by observed failures.
- Admin/demo hardening comes before external review because stale indexes and hidden provider failures can make a correct algorithm look broken.
- Multi-source expansion is gated because the current evidence only validates one structured `伤寒论` workbook.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Confirm final embedding provider, model dimensions, API limits, region/account availability, timeout behavior, and Qdrant hybrid implementation details.
- **Phase 4:** Build a domain evaluation set with customer/doctors; retrieval quality cannot be certified from generic benchmarks.
- **Phase 5:** Validate deployment environment, authentication/network controls for admin APIs, provider-key handling, and privacy/logging expectations.
- **Phase 6:** Research representative future book schemas before committing to multi-source import architecture.

Phases with standard patterns (skip research-phase unless constraints change):
- **Phase 1:** Excel ingestion, Pydantic schemas, deterministic IDs, validation reports, and canonical models are well-understood implementation work.
- **Phase 3:** FastAPI/OpenAPI request/response contracts and evidence projection are standard backend patterns.
- **Phase 5, demo UI only:** A minimal internal search/demo page is standard if no production UX scope is added.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH for FastAPI/Qdrant/pandas/BM25; MEDIUM for provider choice | Package versions and official docs were checked; embedding/reranker provider depends on customer account, region, privacy, and target deployment. |
| Features | HIGH | Strongly grounded in PROJECT.md, source conversation, and explicit v1 requirements. Broader product conventions are secondary. |
| Architecture | MEDIUM-HIGH | Service boundaries, dual-store state, and index lifecycle are standard; exact persistence choice and async job implementation can be scoped during planning. |
| Pitfalls | HIGH for data risks; MEDIUM for legal/compliance framing | Local Excel inspection found sparse `编码` and many multi-formula-like cells; formal privacy/legal review is still outside research scope. |

**Overall confidence:** HIGH for roadmap direction; MEDIUM for model/provider and future multi-book expansion details.

### Gaps to Address

- Embedding/reranker provider: confirm customer-approved API provider, model, dimensions, quota, latency, data-handling terms, and fallback behavior before Phase 2 implementation.
- Formula-code mapping: obtain or define the business formulary mapping table; v1 can return `formula_code: null` with explicit `unmapped` status, but Java integration eventually needs real codes.
- Multi-formula splitting rules: decide how much automatic parsing is acceptable versus `needs_review` workflow before exposing results as production recommendations.
- Evaluation queries: collect representative doctor queries and expected source/formula hits; use them as regression tests for Phase 4.
- Security and privacy controls: define admin authentication/allowlist, log redaction, external provider payload minimization, and retention expectations before external demo.
- Future book schemas: request at least two non-`伤寒论` samples before planning broad multi-book import or raw-text extraction.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project scope, v1 requirements, constraints, out-of-scope items, data source, and integration direction.
- `.planning/research/STACK.md` — recommended Python/FastAPI/Qdrant/BM25 stack, versions, alternatives, and source verification.
- `.planning/research/FEATURES.md` — v1 table stakes, differentiators, anti-features, dependencies, and MVP definition.
- `.planning/research/ARCHITECTURE.md` — service boundaries, data flow, project structure, index lifecycle, and build order.
- `.planning/research/PITFALLS.md` — critical data, scoring, retrieval, operations, safety, and expansion risks.
- `data/任如亮项目对话.txt` — stakeholder intent: retrieval-first v1, Java backend integration, no v1 chat, management APIs, and future 200-book possibility.
- Local Excel inspection of `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` — current sample shape, sparse `编码`, and multi-formula-like `推荐方剂` patterns.

### Secondary (MEDIUM confidence)
- FastAPI official documentation and release notes — OpenAPI-first API surface and current package release basis.
- Qdrant official documentation and release data — dense/sparse vectors, hybrid queries, filtering, point upsert/delete, and current server/client version guidance.
- PyPI package metadata checks — current versions for FastAPI, Pydantic, Uvicorn, qdrant-client, pandas, openpyxl, bm25s, jieba, httpx, ruff, pytest, and related tooling.
- Microsoft Azure AI Search documentation — general hybrid retrieval and score-semantics conventions.
- SentenceTransformers documentation — semantic search and retrieve-then-rerank architecture pattern.

### Tertiary / Validation Needed
- OpenAI embedding documentation and BAAI bge-m3 / bge-reranker-v2-m3 model pages — viable model options, but final selection requires customer/provider validation.
- WHO health-AI guidance, NIST AI RMF, and China PIPL references — useful safety/privacy framing, but not a substitute for legal/compliance review before production.

---
*Research completed: 2026-06-14*
*Ready for roadmap: yes*
