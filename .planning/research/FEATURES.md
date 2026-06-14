# Feature Research

**Domain:** Physician-facing TCM formula retrieval API with demo UI
**Researched:** 2026-06-14
**Confidence:** HIGH for project-specific v1 needs; MEDIUM for broader retrieval-product conventions

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete for demo, Java backend integration, or physician review.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Structured Excel import for Shanghanlun sample data | v1 depends on proving the service can ingest the provided knowledge table, not hand-curated test rows. | MEDIUM | Parse the 22-column workbook from the real sample, skip header/non-data rows, preserve all display fields, and report row counts/errors. |
| Stable knowledge entry IDs | Java backend needs a stable handle for each returned source row; Excel `编码` is not reliably populated. | MEDIUM | Generate internal `entry_id`; preserve source `编码` separately; do not make business integration depend on missing Excel codes. |
| Formula name/code normalization contract | Business backend needs to map returned formulas to its prescription library. | HIGH | `推荐方剂` may contain multiple formulas or mixed text. v1 must define how `formula_name`, `formula_code`, and raw formula text are returned, even if code mapping is partial. |
| Search API for patient presentation | This is the core product: receive symptoms, tongue, pulse, and free notes, then return ranked formulas. | MEDIUM | Accept structured fields plus `topK`; build one normalized query text from symptoms, tongue, pulse, inquiry notes, and supplemental description. |
| TopK ranked retrieval results | Doctors and demo users expect a list of likely matches, not a single brittle answer. | LOW | Default 10; allow caller override within capped bounds. Return rank and score. |
| Evidence fields in every result | Customer cares that recommendations are grounded in classical texts, not generated from nowhere. | LOW | Return original text/article number, syndrome, disease name, treatment method, contraindications, efficacy assessment, and other source columns. |
| Match score with clear semantics | Stakeholders asked to display match percentage, but semantic scores are mainly useful for ordering. | MEDIUM | Return `score` and optionally `display_score`; document that score is ranking/reference, not medical certainty. |
| Index build/rebuild endpoint | Data changes in business tables or Excel need a way to refresh retrieval state. | MEDIUM | Support full rebuild first; item-level update can be added, but rebuild is adequate for roughly 1K-row v1 data. |
| Index status endpoint | Java backend and operators need to know whether the service is ready and what dataset version is loaded. | LOW | Include status, indexed count, last build time, embedding model, index version, and last error. |
| Data maintenance endpoints | Conversation explicitly asks for add/update/delete data point support around the vector index. | MEDIUM | v1 should expose admin APIs, even if update internally reindexes the affected entry or triggers rebuild for simplicity. |
| API documentation | The Java backend and demo page need a stable contract before integration. | LOW | Provide OpenAPI/Swagger plus examples for import, rebuild, status, search, update, and delete. |
| Demo page or sample client | Customer expects to see effect within two to three weeks. | MEDIUM | Minimal internal demo: input symptoms/tongue/pulse, choose topK, show ranked results and evidence. Avoid building full physician workflow. |
| Health check and basic observability | Integration will fail silently without a simple operational surface. | LOW | `/health`, request IDs, structured logs, error responses, and simple timing metrics are enough for v1. |
| Configuration for public embedding/rerank credentials | v1 uses public model APIs with customer-provided API keys. | LOW | Use environment variables; never hard-code keys; expose model/provider in status without exposing secrets. |
| Safe medical framing in responses | This is physician-facing clinical reference, not an autonomous diagnosis product. | LOW | Include disclaimers in docs/demo page; response schema should say `reference_only` or equivalent. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required for a generic retrieval API, but valuable for this TCM formula service.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hybrid retrieval over structured TCM fields | Better recall than pure vector search for terms like formula names, disease names, tongue/pulse phrases, and classical wording. | HIGH | Combine keyword/BM25-style matching with embeddings; weight core symptom/tongue/pulse fields higher than display-only fields. |
| Lightweight reranking | Improves top results when many entries share broad symptoms such as headache or fever. | MEDIUM | Add after baseline retrieval works; use rerank model or deterministic weighted scoring. Keep explainability of ranking inputs. |
| Field-level match explanation | Helps physicians trust why an entry appeared without requiring generative text. | MEDIUM | Return matched fields such as `主病主症`, `复合症`, `舌诊`, `脉象`, `治法`; avoid freeform clinical advice. |
| Query normalization for TCM synonyms | TCM has same-symptom-different-name fields and variant wording; normalization improves recall. | MEDIUM | Use `同症异名` from the source data; start with dictionary expansion from imported columns before model-heavy NLP. |
| Ambiguity handling for broad or mixed symptoms | Doctors may enter sparse or multi-cause symptoms; good retrieval should surface uncertainty. | MEDIUM | Return diverse top results, low-specificity warnings, or `query_quality` hints when input is too broad. Do not ask follow-up questions in v1 unless explicitly scoped later. |
| Source-first result cards | Differentiates from generic AI chat by making classical evidence visible and auditable. | LOW | Demo UI should emphasize formula, syndrome, treatment method, article source, contraindications, and matched symptoms. |
| Dataset/version-aware retrieval | Supports future expansion from one book to up to 200 classics without confusing source provenance. | MEDIUM | Include `source_book`, `source_table`, `dataset_version`, and `entry_id` in index and response even if v1 has only Shanghanlun. |
| Formula splitting preview/report | Surfaces data-quality issues where one source row maps to multiple formulas or unclear formula text. | HIGH | Good candidate for v1.x; helps align with the business prescription library before scaling to more books. |
| Admin import validation report | Saves integration time by making bad rows, missing codes, duplicate formulas, and parse assumptions visible. | MEDIUM | Return warnings instead of silently indexing ambiguous data. Useful for customer data cleanup. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for v1.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Generative TCM chat or diagnosis | Prototype once had chat UI and public model discussion. | Expands liability, testing burden, prompt risk, and scope; conversation explicitly removed it from v1. | Build deterministic retrieval results with evidence; revisit chat after retrieval is validated. |
| Private/local large model deployment | Sounds enterprise-grade and may be monetizable. | Hardware, model ops, latency, and maintenance are out of proportion for a 1K-row v1 demo. | Use public embedding/rerank APIs with environment-based credentials. |
| Autonomous prescription generation | Appears more valuable than retrieval. | The business backend owns prescription details; medical decisions must remain with physicians. | Return formula identifiers, source evidence, treatment method, and contraindications only. |
| Real-time querying of business MySQL for semantic search | Business data is maintained in MySQL, so direct reads seem simpler. | Semantic retrieval needs an index; live SQL scans do not provide vector/rerank behavior and complicate performance. | Provide explicit import/rebuild/sync APIs from business data into retrieval index. |
| Perfect medical confidence percentage | Stakeholders may want a clean 90%/80% display. | Semantic score spacing is dense and not calibrated as clinical probability. | Return rank and score with documented semantics; optionally map scores to display bands. |
| Full CRUD parity with a transactional database | Admin users may ask to edit every indexed field through retrieval service. | Retrieval service should not become the source-of-truth data management system. | Keep source data in business DB/files; retrieval service supports import, rebuild, and index maintenance. |
| Automatic extraction from raw classical texts | Future 200 books make automation tempting. | Requires domain validation, extraction QA, and schema design beyond v1. | Accept customer-curated structured tables; add field mapping after source formats are confirmed. |
| Follow-up questioning workflow | Could improve sparse queries. | Turns retrieval API into a conversational product and changes UI/backend contract. | For v1, return `query_quality` hints and broad-match warnings; add follow-up generation later. |
| Patient record storage | Demo may look more complete with saved cases. | Adds privacy, security, retention, and compliance concerns unrelated to retrieval validation. | Treat search requests as stateless; let the Java business backend own patient records. |
| Large public consumer app features | Common in health apps: accounts, history, favorites, sharing. | The target user is an existing physician workflow through Java backend/demo page. | Build a backend API and minimal demo only. |

## Feature Dependencies

```text
Real Shanghanlun Excel import
    └──requires──> Field mapping and row validation
                       └──requires──> Stable internal entry IDs

Search API
    └──requires──> Indexed knowledge entries
                       └──requires──> Import/build pipeline

Business formula linking
    └──requires──> Formula name/code normalization contract
                       └──requires──> Multi-formula ambiguity handling

Evidence-rich results
    └──requires──> Preserve all source display fields during import

Admin update/delete/rebuild
    └──requires──> Stable entry IDs and index status tracking

Demo page
    └──requires──> Search API, API docs, and sample indexed dataset

Hybrid retrieval
    └──enhances──> Search API
    └──requires──> Field-weighted searchable documents

Reranking
    └──enhances──> Hybrid retrieval
    └──requires──> Baseline candidate retrieval

Generative chat
    └──conflicts──> v1 scope discipline
```

### Dependency Notes

- **Import before search:** Search quality cannot be judged from toy rows; the first validation must use the provided workbook and real columns.
- **Entry IDs before admin endpoints:** Update/delete/rebuild workflows need stable IDs, especially because the source `编码` field may be blank.
- **Formula normalization before Java integration:** Returning only raw `推荐方剂` text risks breaking prescription-library lookup.
- **Evidence preservation before demo:** The demo's trust value comes from showing classical evidence and contraindications, not just formula names.
- **Hybrid retrieval before reranking:** Reranking is useful only after candidate retrieval has enough recall.
- **Chat conflicts with v1:** Chat changes product semantics from retrieval reference to generated medical interaction and should remain out of launch scope.

## MVP Definition

### Launch With (v1)

Minimum viable product needed to validate the concept and support Java backend integration.

- [ ] Parse and import the real Shanghanlun Excel sample with row count, validation warnings, and preserved fields.
- [ ] Build searchable/indexed knowledge entries from core symptom, tongue, pulse, syndrome, disease, and formula fields.
- [ ] Provide stateless search API accepting structured patient presentation and returning ranked topK results.
- [ ] Return formula name/raw formula text, formula code if known, internal entry ID, score/rank, treatment method, syndrome, disease name, original evidence, and contraindications.
- [ ] Provide admin APIs for rebuild/import, status, add/update/delete data point, and health checks.
- [ ] Publish OpenAPI documentation and runnable examples for the Java backend.
- [ ] Deploy a minimal demo page or sample service showing query input and evidence-rich ranked results.

### Add After Validation (v1.x)

Features to add once baseline retrieval is working on real data.

- [ ] Hybrid keyword + semantic retrieval with field weighting - add if pure semantic retrieval misranks broad TCM symptoms.
- [ ] Reranking - add if top 10 contains plausible entries but order is weak.
- [ ] Formula splitting and normalization report - add once business formula library mapping is available.
- [ ] Query-quality hints - add if demos show sparse symptoms produce unclear rankings.
- [ ] Dataset versioning and multi-book source metadata - add before importing the second or third source book.
- [ ] Admin import validation report UI - add when non-developer operators start maintaining source data.

### Future Consideration (v2+)

Features to defer until retrieval value and integration shape are validated.

- [ ] Conversational follow-up and generated explanations - defer until scope, liability, and prompt behavior are explicitly designed.
- [ ] Private model/local deployment - defer until data/security requirements or volume justify infrastructure cost.
- [ ] Automatic raw classic text extraction - defer until curated table schema and quality review workflow are stable.
- [ ] Patient-case history, accounts, or physician workflow management - defer to the business system unless this service becomes a full application.
- [ ] Cross-book conflict resolution and citation ranking - defer until multiple classics are imported and conflicts are observable.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Real Excel import | HIGH | MEDIUM | P1 |
| Stable entry IDs | HIGH | MEDIUM | P1 |
| Formula linking contract | HIGH | HIGH | P1 |
| Search API | HIGH | MEDIUM | P1 |
| Ranked topK results | HIGH | LOW | P1 |
| Evidence-rich result schema | HIGH | LOW | P1 |
| Score/rank semantics | MEDIUM | MEDIUM | P1 |
| Admin rebuild/import/status | HIGH | MEDIUM | P1 |
| API documentation | HIGH | LOW | P1 |
| Minimal demo page/service | HIGH | MEDIUM | P1 |
| Hybrid retrieval | HIGH | HIGH | P2 |
| Reranking | MEDIUM | MEDIUM | P2 |
| Field-level match explanation | HIGH | MEDIUM | P2 |
| Query synonym expansion | MEDIUM | MEDIUM | P2 |
| Dataset/source versioning | MEDIUM | MEDIUM | P2 |
| Formula splitting report | HIGH | HIGH | P2 |
| Generative chat | MEDIUM | HIGH | P3 |
| Private model deployment | LOW for v1 | HIGH | P3 |
| Raw text extraction | MEDIUM later | HIGH | P3 |
| Patient history/accounts | LOW for service | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have or future consideration

## Competitor Feature Analysis

There is no single direct competitor benchmark in the provided materials. For roadmap purposes, compare against adjacent product expectations:

| Feature | Generic Vector Search API | Generic Medical AI Chat | Our Approach |
|---------|---------------------------|-------------------------|--------------|
| Search inputs | Usually free text plus filters | Conversation history and prompts | Structured physician-collected fields plus optional free notes. |
| Result shape | Documents/chunks with scores | Generated answer | Formula-centered ranked rows with source evidence and business linking fields. |
| Trust mechanism | Metadata/citation if configured | Model explanation, often hard to verify | Preserve original classical text, article number, syndrome, treatment method, and contraindications. |
| Data maintenance | Upsert/delete/reindex APIs | Often hidden behind app data layer | Explicit admin endpoints for import, rebuild, status, and point maintenance. |
| v1 risk | Underexplained results | Overgenerated clinical advice | Retrieval-only reference service; physician remains decision maker. |

## Sources

- Project context: `/Volumes/KINGSTON/projects/zyfangji-retrieval-server/.planning/PROJECT.md` (HIGH confidence)
- Source conversation: `/Volumes/KINGSTON/projects/zyfangji-retrieval-server/data/任如亮项目对话.txt` (HIGH confidence)
- Microsoft Azure AI Search hybrid search documentation, for current retrieval convention that hybrid combines keyword and vector search and can use semantic ranking/reranking: https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview (MEDIUM confidence for general ecosystem, not project-specific)
- OpenAPI Specification, for machine-readable HTTP API contract convention used by backend integrations: https://spec.openapis.org/oas/latest.html (MEDIUM confidence for API documentation convention)
- WHO guidance on AI for health, for human oversight and safety framing in clinical AI systems: https://www.who.int/publications/i/item/9789240078871 (MEDIUM confidence for safety framing)

---
*Feature research for: physician-facing TCM formula retrieval API*
*Researched: 2026-06-14*
