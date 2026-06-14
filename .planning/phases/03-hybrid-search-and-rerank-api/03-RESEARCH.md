# Phase 3: Hybrid Search and Rerank API - Research

**Researched:** 2026-06-14
**Domain:** FastAPI retrieval endpoint, BM25/Qdrant hybrid recall, rank fusion, reranking, medical evidence response contracts
**Confidence:** HIGH for existing-code integration and API contracts; MEDIUM for production BGE provider behavior until the reranker provider is selected and benchmarked.

<user_constraints>
## User Constraints

### Locked Decisions

- Phase 3 is the current focus after Phase 2 completed and verified. [VERIFIED: .planning/STATE.md]
- MVP reads local Excel / local structured files; do not assume customer MySQL schema or direct access. [VERIFIED: .planning/STATE.md]
- The retrieval service returns formula identifiers, mapping status, and evidence; Java backend owns patient workflow and prescription composition joins. [VERIFIED: .planning/STATE.md]
- MVP includes BM25 recall, BGE-M3 vector recall, Hybrid Fusion, and BGE-Reranker-v2-m3 reranking. [VERIFIED: .planning/STATE.md]
- Phase 3 must expose a stateless search endpoint with patient presentation fields and bounded `topk`. [VERIFIED: .planning/ROADMAP.md]
- Phase 3 must run BM25 Top50 recall, BGE-M3 Qdrant Top50 recall, hybrid fusion, then BGE-Reranker-v2-m3 reranking. [VERIFIED: .planning/ROADMAP.md]
- Search responses must preserve doctor-facing evidence fields and must not present retrieval scores as medical confidence. [VERIFIED: .planning/ROADMAP.md]
- SQLite active index state is the local source of truth; Qdrant alias alone is not enough. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md]
- Phase 2 status reports reranker as `not_configured`; reranker execution/configuration is Phase 3 scope. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-03-SUMMARY.md]

### Claude's Discretion

- Use RRF or a configurable weighted-score strategy for fusion; recommend RRF as the default because it combines independently scaled BM25 and vector ranks without treating raw scores as comparable. [VERIFIED: .planning/ROADMAP.md] [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/]
- Add provider boundaries and deterministic fakes for the Phase 3 reranker before wiring real BGE-Reranker-v2-m3, matching the Phase 2 embedding-provider testing pattern. [VERIFIED: src/zyfangji_retrieval/indexing/embeddings.py] [ASSUMED]
- Implement search as a read-only FastAPI route and service layer, reusing existing status/settings dependency patterns. [VERIFIED: src/zyfangji_retrieval/api/routes/status.py]

### Deferred Ideas (OUT OF SCOPE)

- Customer MySQL direct access or sync is out of v1 scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Lightweight admin console is out of v1 scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Generative TCM chatbot, medical diagnosis, autonomous prescribing, symptom standardization, and medical NER are out of v1 scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Prescription composition database lookup is out of retrieval-service scope; return formula identifiers/evidence for Java-side joins. [VERIFIED: .planning/REQUIREMENTS.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Stateless search endpoint for patient presentation data and `topk`. | Use `POST /api/search` with Pydantic v2 request/response models and no server-side session state. [VERIFIED: .planning/REQUIREMENTS.md] |
| PIPE-02 | Construct normalized query text from structured patient fields. | Mirror existing labeled-section `retrieval_text` style with query labels for main symptom, symptoms, tongue, pulse, and syndrome. [VERIFIED: src/zyfangji_retrieval/ingestion/retrieval_text.py] |
| PIPE-03 | BM25 keyword recall Top50. | Load active BM25 snapshot from `active.bm25_path`/version, tokenize query with project `jieba+tcm_terms`, call `BM25.retrieve(..., corpus=entry_ids, k=50, show_progress=False)`. [VERIFIED: local introspection of bm25s 0.3.9] |
| PIPE-04 | BGE-M3 vector recall Top50 from Qdrant. | Use active SQLite record for collection/version, embed query via provider, query Qdrant with `query_points(..., query=query_vector, limit=50, with_payload=True)`. [VERIFIED: local introspection of qdrant-client 1.18.0] |
| PIPE-05 | Fuse BM25 and vector candidates. | Use local RRF default over ranks, preserving original signal scores as diagnostics; do not blend raw BM25/vector scores by default. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] |
| PIPE-06 | Rerank fused Top50 using BGE-Reranker-v2-m3. | Define `RerankerProvider` boundary with `rerank(query_text, candidates)`; real provider can use FlagEmbedding `FlagReranker.compute_score`. [CITED: https://huggingface.co/BAAI/bge-reranker-v2-m3] |
| PIPE-07 | Return Top10 default and bounded caller `topk`. | Pydantic validation should default `topk=10`, constrain lower bound 1 and upper bound 50 or lower configured max. [VERIFIED: .planning/ROADMAP.md] |
| PIPE-08 | Handle sparse/broad queries gracefully. | Return ranked results plus `warnings[]` such as `query_too_sparse` or `query_broad`; never fabricate diagnostic certainty. [VERIFIED: .planning/REQUIREMENTS.md] |
| RES-01 | Include rank, retrieval score, score type, IDs, metadata, formula fields, mapping status. | Existing `KnowledgeEntry` and Qdrant payload already preserve these fields except rank/score contract. [VERIFIED: src/zyfangji_retrieval/domain/models.py] |
| RES-02 | Include evidence fields needed by doctors. | Some fields are first-class (`therapy`, disease names, article, contraindication, effect); remaining symptoms/tongue/pulse/aliases are in `raw_record`/`normalized_record`. [VERIFIED: src/zyfangji_retrieval/domain/models.py] |
| RES-03 | Document score semantics as ranking/reference signals only. | Put `score_type` and response-level `score_semantics` in schema; avoid names like confidence/probability. [VERIFIED: .planning/REQUIREMENTS.md] |
| RES-04 | Java-friendly response without business formulary fetch. | Use stable JSON, nullable formula codes, and explicit `formula_mapping_status`. [VERIFIED: .planning/STATE.md] |
| RES-05 | Stable JSON error shapes. | Use custom error model and FastAPI `HTTPException`/exception handler patterns. [CITED: https://fastapi.tiangolo.com/tutorial/handling-errors/] |
</phase_requirements>

## Summary

Phase 3 should add a read-only/stateless search API layer on top of the Phase 2 active index ledger. The planner should not start from Qdrant aliases alone: the verified source of active search state is `SQLiteIndexStateStore.get_active()`, which contains the active index version, Qdrant collection/alias, BM25 path, entry counts, provider ID, model ID, and vector size. [VERIFIED: src/zyfangji_retrieval/persistence/index_state.py] [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md]

The standard implementation shape is: validate request -> build labeled query text -> load active index -> BM25 Top50 -> embed query and Qdrant Top50 -> local RRF fusion -> rerank fused candidates -> project evidence-rich results. RRF should be the default fusion method because BM25 scores, vector similarities, and reranker logits are not naturally comparable absolute scales. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] Reranker output should determine final ordering when available, while raw signal scores remain diagnostic fields named as ranking signals, not medical confidence. [VERIFIED: .planning/REQUIREMENTS.md]

**Primary recommendation:** Build an explicit `search` package with Pydantic contracts, `SearchService`, `BM25Retriever`, `VectorRetriever`, `RRFusion`, `RerankerProvider`, and `EvidenceProjector`; expose only `POST /api/search` in Phase 3.

## Project Constraints (from AGENTS.md)

- MVP is a retrieval service, not a chatbot or diagnosis/prescription generator. [VERIFIED: AGENTS.md]
- Use local Excel/local structured data for v1; do not depend on customer MySQL. [VERIFIED: AGENTS.md]
- API must be stable for Java backend integration and preserve OpenAPI documentation. [VERIFIED: AGENTS.md]
- Retrieval pipeline must include BM25, BGE-M3 vector recall, Hybrid Fusion, and BGE-Reranker-v2-m3 reranking. [VERIFIED: AGENTS.md]
- Retrieval scores are ranking/display signals only, not medical confidence. [VERIFIED: AGENTS.md]
- Responses should preserve source evidence, contraindications, and west-medicine-priority fields when present. [VERIFIED: AGENTS.md]
- Before future file-changing work, use a GSD workflow entry point; this research artifact itself is part of the GSD research workflow. [VERIFIED: AGENTS.md]
- No project-local `.claude/skills` or `.agents/skills` directories were found. [VERIFIED: find .claude/skills .agents/skills]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.12,<3.13` | Service runtime | Repo requires Python 3.12 and previous verification uses a `uv` managed 3.12 environment because system Python is 3.9.6. [VERIFIED: pyproject.toml] [VERIFIED: command probe] |
| FastAPI | pinned `0.136.3` | Search API route and OpenAPI schema | Existing app factory uses FastAPI and current repo pin is tested. Registry currently reports `0.137.0`, but do not update inside Phase 3 unless explicitly planned. [VERIFIED: pyproject.toml] [VERIFIED: PyPI JSON] |
| Pydantic | pinned/current `2.13.4` | Request/response/error schemas | Existing domain and status contracts use Pydantic v2. [VERIFIED: pyproject.toml] |
| qdrant-client | pinned/current `1.18.0` | Vector recall from active Qdrant collection | Local introspection confirms `QdrantClient.query_points` supports vector queries and payload return. [VERIFIED: local package introspection] |
| Qdrant server | `1.18.2` latest release | Vector database | Latest upstream Qdrant release is v1.18.2, published 2026-06-04. [VERIFIED: GitHub releases API] |
| bm25s | pinned/current `0.3.9` | Local BM25 recall | Existing Phase 2 BM25 artifacts use `bm25s.BM25.save/load`; `retrieve` accepts caller-supplied `corpus` IDs and `k`. [VERIFIED: local package introspection] |
| jieba | pinned/current `0.42.1` | Chinese tokenization | Existing tokenizer loads project TCM terms and is used for BM25 indexing. [VERIFIED: src/zyfangji_retrieval/indexing/tokenizer.py] |
| FlagEmbedding | current `1.4.0` but not installed | Optional real BGE reranker adapter | Official BGE reranker docs use `FlagReranker.compute_score`; add only when real local reranker is selected. [VERIFIED: PyPI JSON] [CITED: https://huggingface.co/BAAI/bge-reranker-v2-m3] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | pinned/current `2.14.1` | Search/reranker settings | Add `search_default_topk`, `search_max_topk`, `recall_topk`, `fusion_strategy`, `reranker_provider`, `reranker_model_id`, and reranker timeout settings. [VERIFIED: pyproject.toml] |
| Uvicorn | pinned/current `0.49.0` | ASGI server | Already pinned for running FastAPI service. [VERIFIED: pyproject.toml] |
| pytest | pinned/current `9.1.0` | Contract and service tests | Existing suite uses pytest and has 82 verified tests after Phase 2. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md] |
| ruff | pinned/current `0.15.17` | Linting | Existing verification uses `ruff check src tests`. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local RRF fusion over BM25 + Qdrant results | Qdrant native hybrid `prefetch` + `RrfQuery` | Native Qdrant hybrid is excellent when both dense and sparse vectors live in Qdrant, but Phase 2 BM25 is local `bm25s`; local RRF avoids redesigning the index. [VERIFIED: src/zyfangji_retrieval/indexing/bm25_store.py] [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] |
| Deterministic fake reranker in tests | Real BGE model in unit tests | Real model tests add heavyweight Torch/model downloads and latency; Phase 3 should keep unit tests deterministic and reserve real-model smoke checks for configured environments. [ASSUMED] |
| `POST /api/search` | `GET /search` with query params | Structured patient presentation contains arrays and multiple optional fields; POST JSON is easier and Java-friendly. [ASSUMED] |

**Installation:**

```bash
# No new dependency needed for deterministic Phase 3 tests.

# Add only for real local reranker mode:
uv add FlagEmbedding==1.4.0
```

**Version verification:** Package currentness was checked on 2026-06-14 via PyPI JSON and local package introspection. FastAPI latest is `0.137.0` while the repo pins `0.136.3`; all other listed runtime pins match current registry versions. [VERIFIED: PyPI JSON] [VERIFIED: pyproject.toml]

## Architecture Patterns

### Recommended Project Structure

```text
src/zyfangji_retrieval/
├── api/routes/search.py        # POST /api/search route and dependency wiring
├── domain/search_models.py     # PatientSearchRequest, SearchResponse, SearchResult, APIError
├── search/query.py             # Structured patient fields -> labeled query text + warnings
├── search/bm25.py              # Active BM25 snapshot loading and Top50 recall
├── search/vector.py            # Query embedding + Qdrant Top50 recall
├── search/fusion.py            # RRF/default fusion and optional weighted fusion
├── search/rerank.py            # RerankerProvider protocol + deterministic/disabled adapters
├── search/evidence.py          # KnowledgeEntry/payload -> doctor-facing evidence projection
└── search/service.py           # End-to-end SearchService orchestration
```

### Pattern 1: Active-Index-Gated Search

**What:** Every search request first reads `SQLiteIndexStateStore.get_active()` and verifies a ready active index before touching BM25/Qdrant/reranker. [VERIFIED: src/zyfangji_retrieval/persistence/index_state.py]

**When to use:** All Phase 3 searches.

**Example:**

```python
# Source: existing Phase 2 status pattern
active = index_state_store.get_active()
if active is None or not active.bm25_path or not active.qdrant_collection:
    raise SearchUnavailable("index_not_ready")
```

### Pattern 2: Labeled Query Text Mirrors Retrieval Text

**What:** Build query text using stable labels rather than concatenating raw free text. Existing retrieval text uses labels such as `主症`, `舌诊`, `脉象`, and `证型`. [VERIFIED: src/zyfangji_retrieval/ingestion/retrieval_text.py]

**When to use:** `PIPE-02`, embeddings, BM25 query tokens, and reranker query side.

**Example:**

```python
query_text = "\n\n".join(
    section
    for section in [
        labeled("主症", request.main_symptom),
        labeled("复合症", "\n".join(request.symptoms)),
        labeled("舌诊", request.tongue),
        labeled("脉象", request.pulse),
        labeled("证型", request.syndrome),
    ]
    if section
)
```

### Pattern 3: Candidate Records Carry Signal Provenance

**What:** Internal candidates should preserve `entry_id`, signal ranks, raw scores, fused score, rerank score, and source payload/entry. [VERIFIED: .planning/REQUIREMENTS.md]

**When to use:** Fusion, debugging, response projection, and future quality tests.

**Example:**

```python
class SearchCandidate(BaseModel):
    entry_id: str
    bm25_rank: int | None = None
    bm25_score: float | None = None
    vector_rank: int | None = None
    vector_score: float | None = None
    fused_rank: int | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
```

### Pattern 4: Stable Error Envelope

**What:** Return machine-readable code plus human message and optional details, not raw exceptions. FastAPI supports `HTTPException` detail JSON and custom handlers. [CITED: https://fastapi.tiangolo.com/tutorial/handling-errors/]

**When to use:** Index not ready, invalid query, provider failure, vector store unavailable, reranker unavailable.

**Example:**

```json
{
  "error": {
    "code": "index_not_ready",
    "message": "Active retrieval index is not ready.",
    "details": {"ready": false}
  }
}
```

### Anti-Patterns to Avoid

- **Treating Qdrant alias as the only active-state check:** Phase 2 verification explicitly says SQLite active index is local truth. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md]
- **Blending raw BM25 and vector scores by default:** These scores have different scales; use rank fusion unless a later evaluation calibrates weights. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/]
- **Returning `confidence`, `diagnosis_probability`, or prescription certainty fields:** Scores are ranking/reference signals only. [VERIFIED: .planning/REQUIREMENTS.md]
- **Dropping `needs_review`/`unmapped` formulas:** Mapping ambiguity must remain visible to Java callers. [VERIFIED: .planning/REQUIREMENTS.md]
- **Calling real reranker/model during `/status` or readiness:** Phase 2 status handlers are intentionally read-only and provider-free. [VERIFIED: src/zyfangji_retrieval/api/routes/status.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BM25 scoring | Custom TF-IDF/BM25 implementation | Existing `bm25s` artifacts and `BM25.retrieve` | Phase 2 already indexes and persists `bm25s`; custom ranking risks mismatch and bugs. [VERIFIED: src/zyfangji_retrieval/indexing/bm25_store.py] |
| Chinese tokenization | Regex/character splitting | Existing `tokenize_chinese_text()` with `jieba+tcm_terms` | Project dictionary preserves TCM terms such as formulas and pulse patterns. [VERIFIED: tests/test_bm25_indexing.py] |
| Vector search transport | Raw HTTP calls to Qdrant | `qdrant-client==1.18.0` | Existing code and tests already use qdrant-client models/repository boundary. [VERIFIED: src/zyfangji_retrieval/indexing/qdrant_store.py] |
| Fusion scoring | Ad hoc score addition | RRF default | RRF combines ranks from heterogeneous retrieval systems without raw score calibration. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] |
| Reranker model protocol | Embedding similarity as rerank substitute | BGE-Reranker-v2-m3 provider boundary | Official reranker computes query-passage relevance scores; it is not the same as embedding cosine. [CITED: https://huggingface.co/BAAI/bge-reranker-v2-m3] |
| API validation | Manual dict parsing | Pydantic v2 models/FastAPI response models | Existing service standard uses Pydantic contracts. [VERIFIED: src/zyfangji_retrieval/domain/index_models.py] |

**Key insight:** Phase 3 is orchestration over already-versioned retrieval artifacts. The planner should avoid re-indexing or redesigning storage while implementing search.

## Common Pitfalls

### Pitfall 1: Stale or Mismatched Active Index

**What goes wrong:** Search loads a BM25 path from one index version and Qdrant collection/alias from another. [VERIFIED: .planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md]

**Why it happens:** Code follows Qdrant alias instead of SQLite active record or reloads latest build instead of active build.

**How to avoid:** Resolve all search resources from `ActiveIndexRecord` in one read and include `index_version` in the response metadata.

**Warning signs:** Result count mismatch, missing `entry_id` from SQLite, or readiness passes but search returns empty vector results.

### Pitfall 2: BM25 Entry-ID Alignment Drift

**What goes wrong:** BM25 returns numeric positions but response projection maps them to the wrong entry. [VERIFIED: local introspection of bm25s 0.3.9]

**Why it happens:** Caller forgets to pass `corpus=snapshot.metadata.entry_ids` or reloads entries in a different order.

**How to avoid:** Always call `retrieve([tokens], corpus=snapshot.metadata.entry_ids, k=50, show_progress=False)` and treat returned documents as entry IDs.

**Warning signs:** Result formula/evidence looks unrelated to exact lexical match.

### Pitfall 3: Reranker Failure Breaks All Search

**What goes wrong:** Provider timeout or missing model prevents any results even though BM25/vector recall succeeded. [ASSUMED]

**Why it happens:** Reranker is wired as mandatory without graceful typed failure behavior.

**How to avoid:** Phase requirement says BGE rerank is in the success path, but error behavior should be explicit: either fail with `reranker_unavailable` when configured-required, or return fallback fused results only when a config flag allows degraded mode. [VERIFIED: .planning/ROADMAP.md] [ASSUMED]

**Warning signs:** `/status` says reranker enabled but `/api/search` intermittently returns 500.

### Pitfall 4: Evidence Fields Hidden in Raw Records

**What goes wrong:** Response only returns formula and source article, omitting aliases, tongue, pulse, contraindications, west-medicine-priority, and efficacy fields. [VERIFIED: .planning/REQUIREMENTS.md]

**Why it happens:** `KnowledgeEntry` has some first-class evidence fields, but symptoms/tongue/pulse/aliases and west-medicine-priority require projection from `normalized_record` or `raw_record`.

**How to avoid:** Create explicit `EvidenceFields` model and map from the 22 source headers. Include nulls or empty strings consistently for absent values.

**Warning signs:** Java-side UI cannot display doctor-facing basis without parsing raw record.

### Pitfall 5: Misleading Score Names

**What goes wrong:** API clients interpret score values as medical confidence. [VERIFIED: .planning/REQUIREMENTS.md]

**Why it happens:** Fields named `confidence`, `probability`, or normalized `0..1` reranker scores without context.

**How to avoid:** Use `retrieval_score`, `score_type`, `score_semantics`, and optional `signal_scores`; document that higher only means stronger retrieval/rerank signal within this query.

**Warning signs:** API docs mention diagnosis certainty or prescription recommendation confidence.

## Code Examples

### BM25 Top50 Recall

```python
# Source: bm25s 0.3.9 local introspection and existing BM25IndexStore metadata
snapshot = BM25IndexStore(Path(active.bm25_path).parent).load(active.index_version)
tokens = tokenize_chinese_text(query_text)
documents, scores = snapshot.index.retrieve(
    [tokens],
    corpus=snapshot.metadata.entry_ids,
    k=50,
    show_progress=False,
)
entry_ids = list(documents[0])
```

### Qdrant Top50 Recall

```python
# Source: qdrant-client 1.18.0 local introspection
response = qdrant_client.query_points(
    collection_name=active.qdrant_collection,
    query=query_vector,
    limit=50,
    with_payload=True,
    with_vectors=False,
)
points = response.points
```

### RRF Fusion

```python
# Source: Qdrant hybrid docs describe RRF as rank-position fusion
def rrf_score(rank_zero_based: int, k: int = 60) -> float:
    return 1.0 / (k + rank_zero_based + 1)

fused[entry_id].score += weight * rrf_score(rank)
```

### BGE Reranker Provider

```python
# Source: https://huggingface.co/BAAI/bge-reranker-v2-m3
from FlagEmbedding import FlagReranker

reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
scores = reranker.compute_score(
    [[query_text, candidate_text] for candidate_text in candidate_texts],
    normalize=False,
)
```

### Response Score Semantics

```python
SearchResponse(
    score_semantics=(
        "retrieval_score is a ranking/reference signal for this query only; "
        "it is not medical confidence, diagnosis probability, or prescription certainty."
    ),
    results=results,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single vector search only | Hybrid retrieval combining semantic and lexical signals | Current Qdrant docs describe hybrid dense/sparse fusion through Query API. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] | Planner should keep BM25 exact TCM terms and vector semantic recall both active. |
| Raw score addition | RRF/rank-based fusion | RRF is documented by Qdrant as a hybrid fusion option. [CITED: https://qdrant.tech/documentation/concepts/hybrid-queries/] | Avoid score calibration work in MVP. |
| Reranker as normalized probability | Reranker as query-passage relevance scorer, optionally sigmoid-normalized | BGE reranker docs show raw logits and optional sigmoid normalization. [CITED: https://huggingface.co/BAAI/bge-reranker-v2-m3] | Do not label normalized scores as medical probabilities. |

**Deprecated/outdated:**

- Direct MySQL `LIKE` search is out of v1 and does not satisfy semantic/vector/hybrid requirements. [VERIFIED: .planning/REQUIREMENTS.md]
- Chat/RAG agent frameworks are out of v1 because the product is a deterministic retrieval API. [VERIFIED: AGENTS.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Deterministic fake reranker should be used in unit tests before real BGE wiring. | User Constraints, Standard Stack, Pitfalls | If user requires real reranker in all tests, Phase 3 needs heavyweight model setup and slower CI. |
| A2 | `POST /api/search` is the best endpoint shape. | Standard Stack | If Java backend requires a different path/method, route naming must be adjusted. |
| A3 | Reranker failure behavior can be config-driven between fail-closed and degraded fused-result fallback. | Common Pitfalls | If BGE rerank is strictly mandatory for every result, fallback behavior must be disabled. |

## Open Questions

1. **Real reranker provider availability**
   - What we know: Phase 3 requires BGE-Reranker-v2-m3 reranking; Phase 2 status reports reranker `not_configured`. [VERIFIED: .planning/ROADMAP.md]
   - What's unclear: Whether the deployment will use local FlagEmbedding, a private provider API, or a deterministic/demo adapter.
   - Recommendation: Plan the provider boundary and deterministic tests first, then add real provider configuration only if model runtime/API credentials are available.

2. **TopK upper bound**
   - What we know: Default Top10 is required and caller `topk` must be bounded. [VERIFIED: .planning/ROADMAP.md]
   - What's unclear: Whether max should be 20, 50, or configurable.
   - Recommendation: Use `search_default_topk=10`, `search_max_topk=50`, `recall_topk=50` in settings.

3. **Exact response field naming for west-medicine-priority**
   - What we know: The 22 source headers include `中西先后（先看中医？先看西医？）`, and safety context says preserve west-medicine-priority fields. [VERIFIED: src/zyfangji_retrieval/ingestion/retrieval_text.py] [VERIFIED: user prompt]
   - What's unclear: Preferred English JSON key name for Java consumers.
   - Recommendation: Use `western_medicine_priority` with raw value from that source column.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Python 3.12 environment and tests | Yes | `0.10.4` installed; stack doc mentioned `0.11.21`, so local is older than prior recommendation. [VERIFIED: command probe] | Existing Phase 2 commands work with local `uv`. |
| Python 3.12 | Project runtime | Yes via `uv` env | `/usr/bin/python3` is 3.9.6; `uv` environment has project packages and has been used for verification. [VERIFIED: command probe] | Use `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ...`. |
| Docker | Qdrant server for integration/demo | Yes | Docker `29.3.0`, Compose plugin `5.1.0`. [VERIFIED: command probe] | Use fake Qdrant clients in unit tests if server is not running. |
| Qdrant server | Real vector recall | Not confirmed running | `curl http://localhost:6333/healthz` returned no health payload during audit. [VERIFIED: command probe] | Unit-test vector retriever with fake client; integration/demo must start Qdrant. |
| FlagEmbedding | Real local BGE rerank | No | Not installed in project dependencies. [VERIFIED: pyproject.toml] | Use deterministic provider tests; add dependency/config only when real reranker is selected. |

**Missing dependencies with no fallback:**

- None for deterministic Phase 3 implementation and unit/API tests. [VERIFIED: existing test pattern]

**Missing dependencies with fallback:**

- Running Qdrant server: use fake client for automated unit tests; real demo/search requires service startup.
- Real BGE-Reranker-v2-m3 runtime: use `RerankerProvider` protocol and deterministic adapter until local model/API is configured.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No for Phase 3 MVP unless deployment exposes service beyond trusted backend network. [ASSUMED] | No auth in existing Phase 2 API; document network-bound deployment assumption. |
| V3 Session Management | No | Search endpoint is stateless and should not create sessions. [VERIFIED: .planning/ROADMAP.md] |
| V4 Access Control | Limited | Keep Phase 3 endpoint read-only search; no import/rebuild mutation route. [VERIFIED: src/zyfangji_retrieval/api/routes/status.py] |
| V5 Input Validation | Yes | Pydantic request bounds, string trimming, max list lengths, and stable error model. [VERIFIED: pyproject.toml] |
| V6 Cryptography | No direct crypto | Do not handle secrets except optional provider keys via settings in later provider work. [ASSUMED] |
| V8 Data Protection | Yes | Avoid logging raw patient presentation and do not return generated advice. [VERIFIED: .planning/REQUIREMENTS.md] |
| V10 Malicious Code | Yes for model/provider integration | Do not download model code at request time; pin provider/model configuration. [ASSUMED] |

### Known Threat Patterns for FastAPI Retrieval Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized patient request causes high reranker latency | Denial of Service | Bound `topk`, symptom list length, string lengths, recall limit, and provider timeout. [ASSUMED] |
| Raw patient data appears in logs | Information Disclosure | Do not log request body; log request IDs/counts/status only. [VERIFIED: .planning/REQUIREMENTS.md] |
| Provider failure returns partial results as fresh reranked results | Tampering/Repudiation | Include `pipeline_status`/warnings or fail with stable `reranker_unavailable` error when rerank is required. [VERIFIED: STAT-04 in .planning/REQUIREMENTS.md] |
| Score misinterpretation as medical certainty | Safety/Misuse | Response-level score semantics and no confidence/probability language. [VERIFIED: .planning/REQUIREMENTS.md] |

## Sources

### Primary (HIGH confidence)

- `.planning/REQUIREMENTS.md` - Phase 3 requirement IDs, result contract, safety boundaries.
- `.planning/ROADMAP.md` - Phase 3 scope, plans, and success criteria.
- `.planning/STATE.md` - current phase, decisions, blockers/concerns.
- `.planning/phases/02-index-lifecycle-and-status/02-VERIFICATION.md` - verified active-index source of truth and built state.
- `src/zyfangji_retrieval/domain/models.py` - existing `KnowledgeEntry` contract.
- `src/zyfangji_retrieval/indexing/bm25_store.py` - existing BM25 artifacts and metadata.
- `src/zyfangji_retrieval/indexing/qdrant_store.py` - existing Qdrant payload/index repository.
- `src/zyfangji_retrieval/persistence/index_state.py` - active index ledger.
- `pyproject.toml` and local package introspection - pinned versions and callable APIs.
- PyPI JSON checks on 2026-06-14 - current package versions.
- Qdrant GitHub releases API - latest Qdrant server v1.18.2 published 2026-06-04.

### Secondary (MEDIUM confidence)

- Qdrant Hybrid Queries docs: https://qdrant.tech/documentation/concepts/hybrid-queries/ - Query API, prefetch, RRF, hybrid fusion.
- bm25s README: https://github.com/xhluca/bm25s - retrieval API and corpus mapping pattern, cross-checked by local introspection.
- BGE-Reranker-v2-m3 model card: https://huggingface.co/BAAI/bge-reranker-v2-m3 - FlagEmbedding usage and score semantics.
- FastAPI handling errors docs: https://fastapi.tiangolo.com/tutorial/handling-errors/ - `HTTPException` and error response pattern.
- FastAPI response model docs: https://fastapi.tiangolo.com/tutorial/response-model/ - response models and OpenAPI schema behavior.

### Tertiary (LOW confidence)

- None used as authoritative sources.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - repository pins, local package introspection, PyPI JSON, and Phase 2 verification agree; only FastAPI latest has minor drift from pin.
- Architecture: HIGH - directly follows existing app/status/index modules and verified active-state design.
- Retrieval/fusion patterns: HIGH for RRF and Top50 mechanics; MEDIUM for weighted fusion because no evaluation set exists yet.
- Reranker provider: MEDIUM - official model usage is clear, but local/API deployment resources are not confirmed.
- Security/safety: MEDIUM-HIGH - score/evidence boundaries are verified, but deployment auth/network assumptions remain unconfirmed.

**Research date:** 2026-06-14
**Valid until:** 2026-06-21 for package/provider details; 2026-07-14 for existing-code architecture.
