# Architecture Research

**Domain:** Chinese medicine formula semantic retrieval backend
**Researched:** 2026-06-14
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

The system should be structured as a retrieval service, not as the source-of-truth medical database and not as a chat/diagnosis engine. The Java business backend owns users, patient workflow, prescription display, and formula-detail joins. This service owns knowledge normalization, searchable index construction, ranking, and retrieval result contracts.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Business System                              │
│  Doctor UI → Java Backend → Prescription/Formulary DB                 │
│                    │                                                 │
│                    │ HTTP/OpenAPI                                    │
└────────────────────┼─────────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────────┐
│                    Retrieval Service API                              │
│  Search API          Admin API             Status/Health API           │
│  /search/formulas    /knowledge/import     /index/status               │
│                      /index/rebuild        /jobs/{id}                  │
│                      /points/{id}          /health                     │
├──────────────────────────────────────────────────────────────────────┤
│                         Application Layer                             │
│  Query Builder → Retriever → Reranker/Scorer → Result Projector        │
│  Import Validator → Normalizer → Index Job Orchestrator                │
├──────────────────────────────────────────────────────────────────────┤
│                          Domain Layer                                 │
│  KnowledgeEntry  FormulaMention  SourceBook  SearchQuery  SearchHit    │
│  Stable IDs      Formula code mapping        Field weight policy        │
├──────────────────────────────────────────────────────────────────────┤
│                       Infrastructure Layer                            │
│  Metadata DB       Vector/Search Index       Model Providers           │
│  SQLite/Postgres   Qdrant/Milvus/FAISS       Embedding + optional ranker│
│  Import/job state  Dense/sparse vectors      Public model APIs         │
└──────────────────────────────────────────────────────────────────────┘
```

Recommended implementation shape for phase one: a single deployable Python service with internal modular boundaries. Use FastAPI for the HTTP surface because it produces OpenAPI docs natively, is easy for Java teams to consume, and keeps the first milestone small. Use a real vector store boundary even if phase one starts with an embedded index, so the storage backend can move from local FAISS/SQLite to Qdrant or Milvus without changing the API contract.

### Component Responsibilities

| Component | Responsibility | Boundary |
|-----------|----------------|----------|
| API layer | Stable HTTP contracts for Java backend: search, import, rebuild, status, point delete/update | No embedding logic, no Excel parsing logic, no direct index mutation outside application services |
| Import adapter | Accept Excel/CSV/JSON or Java-pushed rows, validate required fields, preserve raw display fields | Converts external schemas into canonical `KnowledgeEntry` records |
| Normalizer | Cleans symptom, tongue, pulse, formula, source, contraindication, and evidence fields; creates search text | Does not call vector DB; pure transformation and validation |
| ID and formula mapping | Creates stable `entry_id`, `source_id`, `formula_name`, `formula_code`, and optional split records for multi-formula rows | Prevents unstable Excel row numbers from becoming public identifiers |
| Embedding provider | Converts canonical searchable text and query text into dense vectors | Provider abstraction; model/API key can change without touching search API |
| Keyword/sparse encoder | Supports exact and lexical matching for formula names, symptoms, tongue/pulse terms, source titles, and aliases | Keeps semantic search from ignoring important literal Chinese medical terms |
| Index repository | Upsert, delete, rebuild, query, and status operations for vector/search backend | The only component allowed to mutate/search the vector index |
| Metadata repository | Stores canonical records, import batches, index version, job state, and raw fields for result projection | Source of local auditability; not a replacement for the Java formulary DB |
| Retriever | Runs dense, keyword, and optional hybrid retrieval; applies filters such as source book or active index version | Returns candidate entry IDs and raw scores only |
| Reranker/scorer | Optional phase-two stage that reranks top candidates using a rerank model or deterministic field-weight boosts | Produces ranking score for display but must not label it as medical confidence |
| Result projector | Builds response payload: score, formula name/code, treatment method, syndrome, disease, evidence, contraindications, source fields | Does not re-query business prescription details; Java backend owns that join |
| Index job orchestrator | Handles long-running import/rebuild jobs, progress, failure state, and active-index switching | Keeps admin operations asynchronous and observable |

## Recommended Project Structure

Assuming a Python/FastAPI implementation:

```
src/
├── app/
│   ├── main.py                 # FastAPI app assembly
│   ├── api/
│   │   ├── search.py           # Business search endpoints
│   │   ├── admin.py            # Import, rebuild, update, delete endpoints
│   │   └── health.py           # Health, readiness, index status
│   ├── core/
│   │   ├── config.py           # Environment/model/vector-store settings
│   │   ├── errors.py           # API/domain errors
│   │   └── logging.py          # Structured logging setup
│   ├── domain/
│   │   ├── knowledge.py        # KnowledgeEntry, FormulaMention, SourceBook
│   │   ├── search.py           # SearchQuery, SearchHit, scoring metadata
│   │   └── ids.py              # Stable ID and formula mapping policy
│   ├── ingestion/
│   │   ├── excel_reader.py     # Phase-one Excel adapter
│   │   ├── import_service.py   # Batch import workflow
│   │   ├── normalizer.py       # Canonical field normalization
│   │   └── validators.py       # Required fields and schema checks
│   ├── indexing/
│   │   ├── embeddings.py       # Embedding provider boundary
│   │   ├── sparse.py           # Keyword/sparse representation
│   │   ├── repository.py       # Vector store interface
│   │   ├── qdrant_repo.py      # Replaceable vector-store implementation
│   │   └── lifecycle.py        # Rebuild/swap/delete/status operations
│   ├── search/
│   │   ├── query_builder.py    # Patient input → weighted search text
│   │   ├── retriever.py        # Candidate retrieval
│   │   ├── reranker.py         # Optional rerank/boost stage
│   │   └── projector.py        # SearchHit → API response rows
│   └── persistence/
│       ├── db.py               # SQLite/Postgres connection
│       ├── models.py           # Import batches, records, jobs, index versions
│       └── repositories.py     # Metadata repository implementations
├── tests/
│   ├── fixtures/               # Small Excel/JSON sample rows
│   ├── ingestion/
│   ├── indexing/
│   └── search/
└── docs/
    └── api.md                  # Java integration notes generated from OpenAPI
```

### Structure Rationale

- **`api/` is thin:** roadmap phases can change search logic without breaking Java-facing route definitions.
- **`domain/` protects the data contract:** stable IDs, formula mapping, and result field names must be explicit because the source `编码` column is incomplete and `推荐方剂` can contain multiple formulas.
- **`ingestion/` and `indexing/` are separate:** parsing source data and mutating the vector index have different failure modes; this separation makes rebuilds and validation easier to test.
- **`search/` is separate from `indexing/`:** querying, field weighting, reranking, and response projection will evolve faster than the storage backend.
- **`persistence/` stores operational truth:** the service needs batch/job/index-version state even if the business system keeps the authoritative prescription table.

## Architectural Patterns

### Pattern 1: Canonical Record Before Indexing

**What:** Convert every external row into a canonical `KnowledgeEntry` before embedding or storing it in the index.

**When to use:** Always. Phase one has one Excel format; later phases may ingest up to about 200 books with uncertain schema consistency.

**Trade-offs:** Adds a small upfront model layer, but prevents index code from depending on Excel column names and makes future schema mapping realistic.

```typescript
type KnowledgeEntry = {
  entryId: string;
  sourceBook: string;
  sourceRef?: string;
  formulaMentions: Array<{ name: string; code?: string }>;
  searchableText: {
    primarySymptoms: string;
    secondarySymptoms?: string;
    aliases?: string;
    tongue?: string;
    pulse?: string;
    syndrome?: string;
    disease?: string;
  };
  displayFields: Record<string, string | null>;
};
```

### Pattern 2: Dual-Store Retrieval State

**What:** Store canonical rows and import/index metadata in a relational metadata DB; store vectors, sparse terms, and searchable payload in the vector/search index.

**When to use:** From the first build. It keeps result projection stable and allows index rebuilds without losing import audit state.

**Trade-offs:** Two stores require consistency checks, but this is simpler than trying to make the vector database the only operational database.

### Pattern 3: Hybrid Retrieval Pipeline

**What:** Retrieve candidates using semantic vectors plus lexical/sparse matching, then optionally rerank the top candidates.

**When to use:** Chinese medicine terms include short literal signals such as formula names, tongue/pulse descriptions, symptom aliases, and source references. Dense embeddings help with paraphrase; keyword/sparse matching protects exact terminology.

**Trade-offs:** Hybrid retrieval is more complex than pure vector search, but pure vector search is too likely to blur clinically important literal terms. Keep phase one simple: dense topK + keyword boost. Add true sparse/hybrid and rerank as separate later phases.

```
Patient fields
  → weighted query text
  → dense retrieval topN
  → keyword/exact boosts for symptoms, tongue, pulse, formula/source filters
  → optional rerank topN
  → topK projected result rows
```

### Pattern 4: Versioned Index Rebuild and Atomic Activation

**What:** Build a new index version in the background, validate row counts and sample queries, then switch `active_index_version` after the build succeeds.

**When to use:** For full imports/rebuilds and schema changes.

**Trade-offs:** Requires extra storage during rebuild, but avoids search downtime and avoids exposing half-built indexes.

```
import_batch_20260614
  → normalize rows
  → build collection/index: formulas_v20260614_001
  → validate count + sample searches
  → activate formulas_v20260614_001
  → retain previous version for rollback
```

## Data Flow

### Search Request Flow

```
Doctor UI
  ↓
Java Backend
  ↓ POST /search/formulas
Retrieval API
  ↓
Query Builder
  ↓
Embedding Provider + Keyword Extractor
  ↓
Retriever → Vector/Search Index
  ↓
Reranker/Scorer
  ↓
Result Projector → Metadata DB
  ↓
Search response with ranked rows + formula code/name + evidence
  ↓
Java Backend joins prescription details from business DB
  ↓
Doctor UI displays formula details
```

The data direction is intentionally one-way during search. The retrieval service returns references and evidence; it does not update patient records, does not prescribe, and does not fetch prescription composition from the Java system.

### Import and Index Build Flow

```
Java Backend or admin tool
  ↓ POST /knowledge/import or upload Excel
Import Adapter
  ↓
Validator
  ↓
Normalizer and ID Mapper
  ↓
Metadata DB stores canonical records + import batch
  ↓
Index Job Orchestrator starts async build
  ↓
Embedding Provider creates vectors
  ↓
Index Repository upserts points into staging index version
  ↓
Validation checks row count, missing formula codes, sample search behavior
  ↓
Active index version switches only after success
```

### Update/Delete Flow

```
Admin request
  ↓
Validate entry_id or external source key
  ↓
Update Metadata DB canonical record or mark inactive
  ↓
Upsert/delete matching index point
  ↓
Record job/change event
  ↓
Status endpoint exposes operation result
```

For phase one, prefer full rebuild for ambiguous bulk edits and allow targeted delete/upsert only for stable `entry_id` records. This matches the project risk: Excel row identifiers and formula codes are not yet clean enough to support uncontrolled row-level mutation.

## Index Lifecycle

### Index States

| State | Meaning | Search Behavior |
|-------|---------|-----------------|
| `empty` | No usable index exists | Search returns clear `INDEX_NOT_READY` error |
| `building` | New index version is being created | Existing active version serves traffic if present |
| `validating` | Build complete, row counts/sample checks running | Existing active version still serves traffic |
| `active` | Version is serving search | Search uses this version only |
| `retired` | Previous version retained for rollback | Not queried unless manually reactivated |
| `failed` | Build or validation failed | Not activated; failure visible from status API |

### Lifecycle Operations

| Operation | Recommended Behavior | Phase |
|-----------|----------------------|-------|
| Initial import | Parse Excel, normalize, build index, activate after validation | MVP |
| Full rebuild | Create new version, validate, then switch active version | MVP |
| Incremental add | Normalize rows, write metadata, upsert to active index | Phase 2 |
| Targeted update | Replace metadata and upsert same `entry_id`; record change event | Phase 2 |
| Targeted delete | Soft-delete metadata and delete/deactivate index point | Phase 2 |
| Rollback | Reactivate previous index version if retained | Phase 2 |
| Multi-book schema mapping | Map each book source into canonical fields before indexing | Phase 3 |

### Validation Gates

- Imported row count matches expected valid row count from the source file.
- Required retrieval fields are non-empty: symptoms or syndrome/disease terms, source/evidence, formula name if available.
- Formula mapping report lists missing formula codes and multi-formula rows.
- Sample searches return plausible top results for known terms such as `头痛`, `发热`, `舌诊`, `脉象`, and representative formula names.
- Search latency and model/API failures are visible before the demo.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-2k records, demo usage | Single FastAPI service, local metadata DB, local or managed vector index, synchronous search, async rebuild jobs |
| 200k records, multiple books | Managed Qdrant/Milvus or Postgres+pgvector, background worker for imports, explicit schema mapping per book, hybrid retrieval and payload filters |
| 1M+ records or high concurrency | Separate API and worker processes, queue-backed indexing, model-call batching/caching, read replicas or distributed vector store, observability and rollback automation |

### Scaling Priorities

1. **First bottleneck: embedding/model calls during import.** Batch embeddings, cache by normalized text hash, and make rebuild jobs resumable.
2. **Second bottleneck: result quality drift across books.** Add source filters, book-specific field mappings, and evaluation queries before adding more data.
3. **Third bottleneck: vector index rebuild time.** Move rebuilds to a worker and use versioned collections/index aliases.
4. **Fourth bottleneck: Java integration churn.** Freeze response schema early and add optional fields instead of renaming existing ones.

## Anti-Patterns

### Anti-Pattern 1: Real-Time Search Directly Against Business MySQL

**What people do:** Query the Java system's MySQL tables directly for every patient search.

**Why it's wrong:** Semantic retrieval needs embeddings, field weighting, and ranking. Direct SQL scans couple search quality to business schema and will not support vector/rerank lifecycle cleanly.

**Do this instead:** Treat MySQL/business tables as upstream data. Import canonical rows into the retrieval service and build a separate searchable index.

### Anti-Pattern 2: Using Excel Row Number or `编码` as the Only Public ID

**What people do:** Return raw row numbers or the partially populated `编码` column as the stable identifier.

**Why it's wrong:** The project context already notes incomplete codes and multi-formula text. Java needs stable formula references for joins.

**Do this instead:** Generate a stable `entry_id` for retrieval entries and maintain separate `formula_code` mapping for business formulary joins. Report missing/unmapped formula codes.

### Anti-Pattern 3: Pure Dense Vector Search Only

**What people do:** Concatenate row text, embed it, and return nearest neighbors with no lexical safeguards.

**Why it's wrong:** Short Chinese medicine terms, formula names, tongue/pulse vocabulary, and exact source references can be lost or over-smoothed by semantic similarity.

**Do this instead:** Start with dense retrieval plus deterministic keyword boosts; evolve to true hybrid dense+sparse retrieval and reranking after MVP evaluation.

### Anti-Pattern 4: In-Place Index Rebuild

**What people do:** Delete the active index, rebuild it, and let search fail or return partial results during rebuild.

**Why it's wrong:** Admin rebuilds are expected. In-place mutation creates downtime and makes failures hard to roll back.

**Do this instead:** Build a staging index version and atomically activate it after validation.

### Anti-Pattern 5: Returning Scores as Medical Confidence

**What people do:** Display semantic scores as if `0.90` means a clinically reliable recommendation.

**Why it's wrong:** The conversation explicitly notes that semantic scores are useful for ranking but not absolute confidence. Score ranges are often compressed.

**Do this instead:** Return `rank`, `score`, `score_explanation`, and source evidence. Label score as retrieval relevance only.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Java backend | HTTP/OpenAPI JSON | Java sends patient fields and import/update requests; retrieval service returns ranked references and evidence |
| Business prescription DB | Indirect via Java backend | Retrieval service returns `formula_code`/`formula_name`; Java joins prescription composition and display details |
| Embedding model API | Provider interface with batching and timeout controls | Use public model account/API key supplied by customer; cache embeddings by text hash |
| Optional rerank model API | Rerank topN candidates only | Defer until retrieval baseline exists; model calls add latency and cost |
| Vector/search backend | Repository interface | Qdrant/Milvus/FAISS/pgvector should be swappable behind index repository |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Application services | DTOs/Pydantic schemas | API validates request shape; services own behavior |
| Ingestion ↔ Domain | Canonical domain objects | External column names do not leak into search/index logic |
| Domain ↔ Index repository | Search documents and payloads | Index stores retrieval payload and active flags, not full business prescription records |
| Search ↔ Metadata repository | Entry IDs | Search candidates are projected from canonical metadata before response |
| Index job orchestrator ↔ API | Job IDs/status | Long operations should return quickly and expose progress/failure |

## Suggested Build Order and Dependencies

1. **Define canonical domain model and API contract**
   - Depends on: confirmed phase-one Excel columns and response fields.
   - Produces: `KnowledgeEntry`, `SearchRequest`, `SearchResponse`, import job/status schemas.
   - Roadmap implication: do this before any vector store work so Java integration and tests have a stable target.

2. **Implement Excel import, validation, normalization, and metadata persistence**
   - Depends on: canonical model.
   - Produces: import report with valid rows, rejected rows, missing formula codes, and multi-formula warnings.
   - Roadmap implication: this de-risks the known data quality issues before ranking quality is evaluated.

3. **Build minimal index lifecycle**
   - Depends on: normalized records and metadata persistence.
   - Produces: initial build, rebuild, status, active index version, row-count validation.
   - Roadmap implication: admin APIs should land before search polishing because data will change during demo preparation.

4. **Implement baseline search**
   - Depends on: active index and embedding provider.
   - Produces: topK retrieval with ranked formula rows, evidence, contraindications, and display fields.
   - Roadmap implication: MVP demo can happen here if results are plausible.

5. **Add hybrid boosts and query weighting**
   - Depends on: baseline search and sample query evaluation.
   - Produces: better handling for exact symptoms, aliases, tongue/pulse, formula names, and source filters.
   - Roadmap implication: should follow observed result errors, not be overbuilt before sample testing.

6. **Add update/delete and operational admin features**
   - Depends on: stable IDs and index lifecycle.
   - Produces: point-level upsert/delete, job history, rollback, and index diagnostics.
   - Roadmap implication: targeted mutation is lower priority than rebuild for phase one unless Java backend requires it immediately.

7. **Prepare multi-book schema mapping**
   - Depends on: confirmation that future books share fields or can be mapped.
   - Produces: source-specific adapters that map into canonical fields.
   - Roadmap implication: should be a separate phase because schema uncertainty is the largest expansion risk.

## Sources

- Project context: `/Volumes/KINGSTON/projects/zyfangji-retrieval-server/.planning/PROJECT.md` — HIGH confidence for scope, constraints, and known data risks.
- Source conversation: `/Volumes/KINGSTON/projects/zyfangji-retrieval-server/data/任如亮项目对话.txt` — HIGH confidence for integration direction, Java backend boundary, index maintenance expectations, and phase-one non-chat scope.
- FastAPI official documentation, Features/OpenAPI: https://fastapi.tiangolo.com/features/ — HIGH confidence for OpenAPI-first API surface recommendation.
- Qdrant official documentation, Filtering: https://qdrant.tech/documentation/concepts/filtering/ — HIGH confidence that vector search can use structured payload filters.
- Qdrant official documentation, Points: https://qdrant.tech/documentation/concepts/points/ — HIGH confidence for point upsert/delete lifecycle concepts.
- Qdrant official documentation, Hybrid Queries: https://qdrant.tech/documentation/search/hybrid-queries/ — HIGH confidence for dense+sparse/hybrid retrieval pattern.
- SentenceTransformers official documentation, Semantic Search: https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html — MEDIUM-HIGH confidence for retrieve-then-rerank architecture pattern.

---
*Architecture research for: 中医方剂检索系统 / semantic retrieval backend*
*Researched: 2026-06-14*
