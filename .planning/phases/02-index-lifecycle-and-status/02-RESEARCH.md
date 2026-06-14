# Phase 2: Index Lifecycle and Status - Research

**Researched:** 2026-06-14  
**Domain:** 本地索引生命周期、Qdrant 向量写入、BM25 中文词法索引、状态/健康可见性  
**Confidence:** HIGH

## User Constraints

- MVP 读取本地 Excel / 本地结构化文件，不依赖客户 MySQL。 [VERIFIED: .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md]
- Phase 1 已经提供 SQLite/JSONL 本地元数据、`KnowledgeEntry`、`retrieval_text` 和 `load_entries_for_rebuild()`，Phase 2 应从本地元数据重建索引。 [VERIFIED: .planning/phases/01-local-data-contract-and-ingestion/01-VERIFICATION.md, src/zyfangji_retrieval/ingestion/importer.py]
- Phase 2 只做索引构建、验证、激活和状态检查；不要实现最终 `/search`、Hybrid Fusion 或 reranker API。 [VERIFIED: .planning/ROADMAP.md]
- Phase 2 必须覆盖 IDX-01 到 IDX-06、STAT-01 到 STAT-04。 [VERIFIED: .planning/REQUIREMENTS.md]
- Java 后端需要稳定 HTTP API 和接口文档，但一期不是聊天机器人，也不生成诊疗建议。 [VERIFIED: AGENTS.md]
- 检索分数只能作为排序/参考信号，不解释为医学置信度；结果需要保留典籍依据和风险字段。 [VERIFIED: AGENTS.md]

## Project Constraints (from AGENTS.md)

- 一期目标是基于现有《伤寒论》Excel 样例数据交付可演示检索服务和接口文档。 [VERIFIED: AGENTS.md]
- MVP 检索链路目标包括 BM25、BGE-M3 向量召回、Hybrid Fusion、BGE-Reranker-v2-m3 和 TopK 方剂返回，但 Phase 2 只铺好索引基础。 [VERIFIED: AGENTS.md, .planning/ROADMAP.md]
- 当前 GSD 约束要求文件变更走规划/执行流程；本次产物是 Phase 2 planning research，不改业务代码。 [VERIFIED: AGENTS.md]
- 项目内未发现 `CLAUDE.md`、`.claude/skills/` 或 `.agents/skills/` 项目级技能。 [VERIFIED: shell `test -f`, `find`]

## Summary

Phase 2 应把“可重建本地元数据”推进成“可激活索引版本”。 [VERIFIED: Phase 1 verification, ROADMAP] 推荐新增独立 indexing 子系统：从 `load_entries_for_rebuild()` 读取 `KnowledgeEntry`，通过可替换 `EmbeddingProvider` 生成 BGE-M3 兼容 dense vectors，写入版本化 Qdrant collection，并同时生成版本化 BM25 本地索引。 [VERIFIED: src/zyfangji_retrieval/ingestion/importer.py; CITED: https://github.com/qdrant/qdrant-client; CITED: https://github.com/xhluca/bm25s]

激活必须是“全部构建成功 + 校验通过 + 状态元数据更新”后的显式步骤。 [VERIFIED: IDX-02, STAT-04] Qdrant 官方 collection alias 支持后台构建新 collection 后切换别名，适合向量索引的零停机版本切换；但 BM25 是本地文件索引，所以系统仍需要 SQLite 中的 `active_index_version` 作为统一事实来源。 [CITED: https://qdrant.tech/documentation/concepts/collections/#collection-aliases; VERIFIED: Phase 2 scope]

**Primary recommendation:** 计划 Phase 2 为三个可验收计划：`02-01` embedding provider + Qdrant 仓储，`02-02` BM25 + versioned rebuild/activation，`02-03` FastAPI/Typer status + readiness + failure visibility。 [VERIFIED: .planning/ROADMAP.md]

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IDX-01 | 从本地 normalized entries 构建独立检索索引 | 使用 Phase 1 `load_entries_for_rebuild()` 作为唯一输入，禁用客户 DB 依赖。 [VERIFIED: importer.py, REQUIREMENTS.md] |
| IDX-02 | full rebuild 创建新版本，校验成功后激活 | 新增 `index_builds`、`active_index`、版本化 Qdrant collection 和 BM25 目录。 [VERIFIED: ROADMAP; CITED: Qdrant aliases docs] |
| IDX-03 | 暴露 readiness、active version、count、provider/model、build time、last error | 定义 `IndexStatus` schema 和 `/status`、`/health/ready`，CLI `index-status` 输出同一 JSON。 [VERIFIED: REQUIREMENTS.md] |
| IDX-04 | BGE-M3 semantic embeddings 通过可替换接口 | `EmbeddingProvider` protocol 返回 vectors + provider/model/dimensions；测试用 deterministic provider。 [CITED: BAAI bge-m3 README; VERIFIED: tests need deterministic behavior] |
| IDX-05 | dense vectors + payload metadata 写入 Qdrant | Qdrant client 支持 create collection、upsert/upload points、payload；payload 放 `entry_id`、source/formula/status/evidence 摘要。 [CITED: qdrant-client README; CITED: Qdrant points/collections docs] |
| IDX-06 | BM25 中文分词词法索引 | `jieba` tokenizer + project TCM dictionary + `bm25s` persisted index；只建索引和可 inspect，不实现 Phase 3 recall endpoint。 [VERIFIED: PyPI JSON; CITED: bm25s README] |
| STAT-01 | lightweight status endpoint | `/status` 返回 model/provider/vector_store/retrieval_strategy/knowledge_count/index_version/update_time。 [VERIFIED: REQUIREMENTS.md] |
| STAT-02 | health/readiness endpoint | `/health/live` 只检查进程，`/health/ready` 检查 active version、BM25 文件、Qdrant collection/alias、count 一致性。 [VERIFIED: deployment integration need in REQUIREMENTS.md] |
| STAT-03 | import/rebuild failure 可见 | `index_builds.last_error`、CLI/API error JSON 和 status last_error。 [VERIFIED: REQUIREMENTS.md] |
| STAT-04 | provider failure 清晰报错，不把 stale/partial 当 fresh | build 失败保留旧 active version，failed version 不激活，ready 可显示 stale active + last failed build。 [VERIFIED: REQUIREMENTS.md] |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `qdrant-client` | 1.18.0, uploaded 2026-05-11 | Python Qdrant client | 支持同一 API 连接 server 或 local mode，适合生产 Docker 与单测替身。 [VERIFIED: PyPI JSON; CITED: https://github.com/qdrant/qdrant-client] |
| Qdrant server | 1.18.x target | Vector store | 支持 collection、payload、named/sparse vectors、aliases；Phase 2 使用 dense collection + alias。 [CITED: https://qdrant.tech/documentation/concepts/collections/] |
| `bm25s` | 0.3.9, uploaded 2026-05-13 | 本地 BM25 索引 | README 显示可 tokenize/index/retrieve/save/load，适合本地版本化文件索引。 [VERIFIED: PyPI JSON; CITED: https://github.com/xhluca/bm25s] |
| `jieba` | 0.42.1, uploaded 2020-01-20 | 中文分词 | 当前 PyPI 版本稳定但较老；用项目词典补足中医术语。 [VERIFIED: PyPI JSON] |
| `fastapi` | 0.136.3, uploaded 2026-05-23 | 状态/健康 HTTP API | 与项目 Java 后端集成和 OpenAPI 文档目标匹配。 [VERIFIED: PyPI JSON; VERIFIED: AGENTS.md] |
| `uvicorn` | 0.49.0, uploaded 2026-06-03 | ASGI runtime | FastAPI demo 服务运行时。 [VERIFIED: PyPI JSON] |
| `pydantic-settings` | 2.14.1, uploaded 2026-05-08 | 配置 | 管理 Qdrant URL、collection prefix、embedding provider、维度、BM25 path。 [VERIFIED: PyPI JSON] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | 0.28.1 | 外部 embedding API client | 仅当选择 HTTP embedding provider 时添加 provider 实现。 [VERIFIED: PyPI JSON] |
| `orjson` | 3.11.9 | JSON response acceleration | Phase 2 可先不加；Phase 3 payload 变大后再启用。 [VERIFIED: PyPI JSON] |
| `pytest` | 9.1.0 | 单元/合同测试 | 当前项目已使用 pytest，Phase 2 继续沿用。 [VERIFIED: pyproject.toml; VERIFIED: PyPI JSON] |
| `ruff` | 0.15.17 | lint | 当前项目已使用 ruff。 [VERIFIED: pyproject.toml; VERIFIED: PyPI JSON] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `qdrant-client` fake/local mode in unit tests | Docker Qdrant in every test | Docker 更接近真实服务，但慢且依赖环境；单元测试应 fake，少量 smoke 可 Docker。 [CITED: qdrant-client README; VERIFIED: environment audit] |
| `bm25s` local index | Elasticsearch/OpenSearch | ES 更重，超出本地 MVP；Phase 2 只需构建本地词法索引。 [VERIFIED: project stack research in AGENTS.md] |
| `jieba` tokenizer wrapper | `bm25s.tokenize()` 默认英文示例 | README 示例偏英文 stopwords/stemmer；中文中医术语需要自定义 tokenizer。 [CITED: bm25s README; VERIFIED: DATA-06 Chinese fields] |

**Installation:**

```bash
uv add "qdrant-client==1.18.0" "bm25s==0.3.9" "jieba==0.42.1" "fastapi==0.136.3" "uvicorn==0.49.0" "pydantic-settings==2.14.1"
```

## Recommended Module Layout

```text
src/zyfangji_retrieval/
├── api/
│   ├── app.py                 # FastAPI app factory and router registration [ASSUMED]
│   └── routes/status.py       # /status, /health/live, /health/ready [ASSUMED]
├── config.py                  # pydantic-settings app/index config [ASSUMED]
├── domain/
│   └── index_models.py        # IndexVersion, IndexBuildReport, IndexStatus [ASSUMED]
├── indexing/
│   ├── embeddings.py          # EmbeddingProvider protocol and deterministic test provider [ASSUMED]
│   ├── qdrant_store.py        # QdrantVectorIndex repository [ASSUMED]
│   ├── bm25_store.py          # BM25 builder/persistence/metadata [ASSUMED]
│   ├── tokenizer.py           # jieba tokenizer + TCM dictionary loading [ASSUMED]
│   ├── lifecycle.py           # build_validate_activate orchestration [ASSUMED]
│   └── validation.py          # count/dimension/payload/file checks [ASSUMED]
└── persistence/
    └── index_state.py         # SQLite index_builds and active_index metadata [ASSUMED]
```

These filenames are recommendations, not existing files. [VERIFIED: `find src tests`]

## Architecture Patterns

### Pattern 1: Versioned Build, Then Activate

**What:** Generate `index_version = idx-YYYYMMDDHHMMSS[-NN]`, build Qdrant collection `zyfangji_entries_{version}` and BM25 directory `var/indexes/bm25/{version}`, validate both, then update Qdrant alias and SQLite active metadata. [CITED: Qdrant collection aliases docs; VERIFIED: IDX-02]

**When to use:** Every full rebuild, including rebuilding from the same metadata version. [VERIFIED: Phase 1 supports version-specific rebuild source]

**Example:**

```python
# Source: Qdrant client README + project lifecycle recommendation
class EmbeddingProvider(Protocol):
    provider_id: str
    model_id: str
    vector_size: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        ...

report = lifecycle.rebuild(
    entries=load_entries_for_rebuild(db_path, index_version=metadata_version),
    embedding_provider=provider,
    activate=True,
)
```

### Pattern 2: Repository Boundary Around Qdrant

**What:** Keep Qdrant client calls inside `QdrantVectorIndex`; tests assert repository calls through a fake or `QdrantClient(":memory:")`. [CITED: qdrant-client README]

**When to use:** Unit tests for payload mapping, vector dimension validation, failed upserts, and activation behavior. [VERIFIED: current tests are local/pytest-only]

**Example:**

```python
# Source: qdrant-client README local mode pattern
client = QdrantClient(":memory:")
store = QdrantVectorIndex(client=client, collection_prefix="zyfangji_entries")
```

### Pattern 3: Explicit Status Model Shared by CLI and API

**What:** `IndexStatus` is built from SQLite active metadata plus lightweight Qdrant/BM25 probes, then rendered by both Typer and FastAPI. [VERIFIED: current CLI pattern in src/zyfangji_retrieval/cli.py]

**When to use:** `/status`, `/health/ready`, and `zyfangji-retrieval index-status`. [VERIFIED: STAT-01, STAT-02]

### Anti-Patterns to Avoid

- **Activating by overwriting files in place:** It can expose partial BM25 files if the process crashes; write to a temp version directory and rename/record after validation. [VERIFIED: STAT-04]
- **Using Qdrant alias as the only active-version state:** It ignores BM25 and status metadata; SQLite must remain the unified active source. [VERIFIED: Phase 2 includes Qdrant and BM25]
- **Embedding provider calls inside API/status handlers:** Status must be cheap and not fail because a model provider is temporarily unavailable. [VERIFIED: STAT-02, STAT-04]
- **Returning search results in Phase 2:** Search endpoint, Top50 recall, fusion, and rerank are Phase 3 requirements. [VERIFIED: ROADMAP]

## Data Models

| Model | Key Fields | Notes |
|-------|------------|-------|
| `IndexBuildStatus` | `building`, `validated`, `active`, `failed` | Use literals/enums for stable API output. [ASSUMED] |
| `IndexBuildRecord` | `index_version`, `metadata_version`, `entry_count`, `vector_count`, `bm25_doc_count`, `provider_id`, `model_id`, `vector_size`, `started_at`, `finished_at`, `last_error` | Stored in SQLite. [ASSUMED] |
| `ActiveIndexRecord` | `index_version`, `activated_at`, `qdrant_collection`, `qdrant_alias`, `bm25_path`, `metadata_version` | Single active row or key-value table. [ASSUMED] |
| `EmbeddingBatchResult` | `texts_count`, `vectors`, `provider_id`, `model_id`, `vector_size` | Validate `len(vectors) == len(entries)` and vector dimension. [ASSUMED] |
| `IndexStatus` | `ready`, `active_version`, `indexed_count`, `model_provider`, `model_id`, `vector_store`, `retrieval_strategy`, `last_build_time`, `updated_at`, `last_error` | Directly covers IDX-03/STAT-01. [VERIFIED: REQUIREMENTS.md] |

## CLI/API Surfaces

### CLI

| Command | Purpose | Output |
|---------|---------|--------|
| `index-rebuild --db-path ... --activate/--no-activate` | Build Qdrant + BM25 from local metadata. [VERIFIED: IDX-02] | `IndexBuildReport` JSON. [ASSUMED] |
| `index-status --db-path ...` | Show active version and latest build failure. [VERIFIED: STAT-01] | `IndexStatus` JSON. [ASSUMED] |
| `index-validate --index-version ...` | Re-run count/dimension/file/Qdrant checks. [VERIFIED: IDX-02] | validation JSON. [ASSUMED] |

### HTTP

| Endpoint | Purpose | Status Behavior |
|----------|---------|-----------------|
| `GET /health/live` | Process liveness for deployment checks. [VERIFIED: STAT-02] | 200 if app process can answer. [ASSUMED] |
| `GET /health/ready` | Readiness for Java backend. [VERIFIED: STAT-02] | 200 only when active index exists and probes pass; 503 otherwise. [ASSUMED] |
| `GET /status` | Operator/API integration status. [VERIFIED: STAT-01] | 200 with `ready=false` allowed when not ready. [ASSUMED] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector DB storage/search metadata | Custom vector files | Qdrant + qdrant-client | Qdrant already handles collection, payload and point upserts. [CITED: Qdrant docs] |
| BM25 scoring arrays | Custom BM25 implementation | `bm25s` | Library supports tokenized corpus, retrieval, save/load. [CITED: bm25s README] |
| Chinese segmentation | Manual substring splitter | `jieba` wrapper + project dictionary | Chinese symptoms/formula terms need tokenization beyond whitespace. [VERIFIED: DATA-06 fields are Chinese] |
| Embedding provider mocks | Real BGE calls in unit tests | `EmbeddingProvider` protocol + deterministic fake | Provider failures must be tested deterministically. [VERIFIED: STAT-04] |
| Runtime settings parsing | `os.environ` scattered reads | `pydantic-settings` | Central config keeps provider/Qdrant/BM25 paths inspectable. [VERIFIED: PyPI JSON] |

**Key insight:** Phase 2 complexity is lifecycle consistency, not retrieval scoring; custom storage/scoring/provider glue increases partial-index and stale-status risk. [VERIFIED: IDX/STAT requirements]

## Common Pitfalls

### Pitfall 1: Partial Index Becomes Active

**What goes wrong:** Qdrant collection is partly written or BM25 save fails, but status reports the new version as active. [VERIFIED: STAT-04]  
**How to avoid:** Mark build `building`, write to version-specific targets, validate counts/dimensions/files, then atomically update active metadata. [ASSUMED]  
**Warning signs:** `active_version` equals latest failed build, `indexed_count` differs between SQLite/Qdrant/BM25. [ASSUMED]

### Pitfall 2: Unit Tests Require Running Qdrant

**What goes wrong:** CI/local tests fail when Docker/Qdrant is absent. [VERIFIED: environment audit]  
**How to avoid:** Test lifecycle with fake repository and deterministic provider; reserve Qdrant local mode or Docker for optional smoke. [CITED: qdrant-client README]

### Pitfall 3: BM25 Tokenization Loses TCM Exact Terms

**What goes wrong:** Important terms like `太阳病`、`麻黄汤`、`脉浮紧` are split poorly. [ASSUMED]  
**How to avoid:** Add `indexing/tokenizer.py`, load a project dictionary, and test exact term tokens. [ASSUMED]

### Pitfall 4: Provider Metadata Missing

**What goes wrong:** Status cannot explain which model/dimension produced active vectors. [VERIFIED: IDX-03, STAT-01]  
**How to avoid:** Persist provider_id, model_id, vector_size, batch size, and build timestamps with every index build. [ASSUMED]

### Pitfall 5: Phase 2 Accidentally Implements Search

**What goes wrong:** Index build plans expand into recall/fusion/rerank, delaying status/lifecycle reliability. [VERIFIED: ROADMAP]  
**How to avoid:** Phase 2 may add validation probes and maybe top-level counts, but no patient query endpoint and no ranked result contract. [VERIFIED: ROADMAP]

## Code Examples

### Qdrant Local/Test Client

```python
# Source: https://github.com/qdrant/qdrant-client
from qdrant_client import QdrantClient

client = QdrantClient(":memory:")
```

### BM25 Save/Load Pattern

```python
# Source: https://github.com/xhluca/bm25s
retriever = bm25s.BM25()
retriever.index(tokenized_corpus)
retriever.save(str(index_path), corpus=corpus_metadata)
loaded = bm25s.BM25.load(str(index_path), load_corpus=True)
```

### Deterministic Embedding Provider for Tests

```python
# Source: project testing recommendation
import hashlib


class DeterministicEmbeddingProvider:
    provider_id = "test"
    model_id = "deterministic-bge-m3-compatible"
    vector_size = 4

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([digest[i] / 255.0 for i in range(self.vector_size)])
        return vectors
```

## Plan Decomposition Guidance

| Plan | Scope | Must Verify |
|------|-------|-------------|
| 02-01 | Add settings, `EmbeddingProvider`, deterministic provider, Qdrant repository, vector payload mapping. [VERIFIED: ROADMAP] | Unit tests for dimension mismatch, provider failure, payload fields, no Docker required. [ASSUMED] |
| 02-02 | Add BM25 tokenizer/store, SQLite index-state tables, rebuild/validate/activate lifecycle, CLI `index-rebuild`. [VERIFIED: ROADMAP] | Failed provider/BM25/Qdrant build does not change active version; successful build count equals Phase 1 entries. [VERIFIED: STAT-04] |
| 02-03 | Add FastAPI app/status/health/readiness, CLI `index-status`, visible last error. [VERIFIED: ROADMAP] | Readiness 503 with no active index, 200 after active index, status includes provider/model/count/version/error. [VERIFIED: STAT-01, STAT-02] |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rebuild active vector collection in place | Build new Qdrant collection, then switch alias | Qdrant docs document collection aliases for seamless version switching. [CITED: Qdrant collection aliases docs] | Planner should include versioned collections and alias update. [ASSUMED] |
| Real provider in all tests | Provider protocol + deterministic fake | Driven by Phase 2 provider-failure requirements. [VERIFIED: STAT-04] | Tests can cover failures without API keys/GPU. [ASSUMED] |
| Workbook parse during rebuild | Rebuild from SQLite metadata | Phase 1 implemented `load_entries_for_rebuild()`. [VERIFIED: importer.py] | Phase 2 plans should not read Excel directly. [VERIFIED: ING-05] |

**Deprecated/outdated:**

- Direct customer MySQL search is out of scope for v1. [VERIFIED: PROJECT.md, REQUIREMENTS.md]
- LangChain/LlamaIndex-style agent orchestration is not needed for Phase 2 index lifecycle. [VERIFIED: AGENTS.md stack guidance]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact filenames under `api/`, `indexing/`, and `persistence/index_state.py` are recommended new files. | Recommended Module Layout | Planner may choose different names while preserving boundaries. |
| A2 | HTTP readiness should return 503 when no active index exists. | CLI/API Surfaces | Deployment expectations may prefer 200 with `ready=false`; confirm before implementation. |
| A3 | TCM dictionary terms include `太阳病`, `麻黄汤`, `脉浮紧`. | Common Pitfalls | Tokenization tests may need terms from real workbook instead. |
| A4 | SQLite active metadata should be the unified active-version source. | Architecture Patterns | A future service-discovery strategy could move active state elsewhere. |
| A5 | Proposed `IndexBuildStatus`, `IndexBuildRecord`, `ActiveIndexRecord`, `EmbeddingBatchResult`, and `IndexStatus` field sets are the right minimal schemas. | Data Models | Planner may need to add/remove fields after implementation details settle. |
| A6 | Proposed CLI commands `index-rebuild`, `index-status`, and `index-validate` are the right operator surface. | CLI/API Surfaces | Planner may merge validation into rebuild/status commands instead. |
| A7 | Recommended temporary directories, atomic rename/record behavior, and validation ordering are sufficient for local consistency. | Architecture Patterns, Common Pitfalls | Edge cases on the external volume or Windows-like filesystems may need different file handling. |
| A8 | Security controls can keep rebuild as local CLI/read-only HTTP status in Phase 2. | Security Domain | If rebuild is exposed via HTTP earlier, auth/rate limiting become Phase 2 requirements. |
| A9 | Proposed test filenames and exact assertions are the right decomposition. | Testing Strategy | Planner may reorganize tests while preserving behavior coverage. |
| A10 | Deferring Qdrant sparse vectors and keeping local BM25 is the right Phase 2 boundary. | Open Questions | If product leadership demands BGE-M3 sparse retrieval now, Phase 2 scope grows. |

## Open Questions (RESOLVED)

1. **BGE-M3 execution mode**
   - What we know: BGE-M3 model card lists 1024 dimension and dense/sparse/ColBERT support. [CITED: https://huggingface.co/BAAI/bge-m3]
   - What's unclear: local FlagEmbedding, ModelScope, or external HTTP provider has not been selected. [VERIFIED: STATE.md blocker]
   - Recommendation: Phase 2 implement provider boundary and deterministic provider first; make real provider config-driven. [ASSUMED]
   - RESOLVED: Phase 2 plans only the provider boundary, deterministic provider, model/provider metadata, and configuration fields. A real local/API BGE-M3 provider remains config-driven and can be selected later without blocking Phase 2 execution.

2. **Should Qdrant sparse vectors be used now?**
   - What we know: Qdrant supports sparse vectors and BGE-M3 can produce lexical weights. [CITED: Qdrant collections docs; CITED: BGE-M3 README]
   - What's unclear: Roadmap explicitly asks BM25 lexical indexing, not Qdrant sparse lexical retrieval, for Phase 2. [VERIFIED: IDX-06]
   - Recommendation: Use local BM25 in Phase 2; defer Qdrant sparse vectors unless Phase 3 quality demands it. [ASSUMED]
   - RESOLVED: Phase 2 uses local `bm25s` + `jieba` for lexical indexing and dense Qdrant vectors only. Qdrant sparse vectors are deferred unless Phase 3 retrieval-quality work reopens the decision.

3. **FastAPI app timing**
   - What we know: Phase 2 STAT requirements include endpoints, and current project has no FastAPI dependency. [VERIFIED: pyproject.toml, REQUIREMENTS.md]
   - What's unclear: Whether Phase 2 should add full app factory or only minimal status app. [ASSUMED]
   - Recommendation: Add minimal app factory and status router now; search router waits for Phase 3. [ASSUMED]
   - RESOLVED: Phase 2 adds a minimal read-only FastAPI app factory with `/status`, `/health/live`, and `/health/ready`. `/health/ready` returns HTTP 503 when no active index exists or probes fail; `/status` always returns JSON with `ready=false` instead of failing. Search, hybrid fusion, reranker execution, and HTTP rebuild/import mutation wait for later phases.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `uv` | dependency and test execution | yes | 0.10.4 | none needed. [VERIFIED: shell `uv --version`] |
| Docker | Qdrant server smoke/demo | yes | 29.3.0 | Unit tests use fake/local Qdrant client. [VERIFIED: shell `docker --version`; CITED: qdrant-client README] |
| Qdrant CLI/server process | real vector store | no CLI found | — | Use Docker for smoke, fake/local client for unit tests. [VERIFIED: shell `command -v qdrant`] |
| Python system | shell default | yes | 3.9.6 | Use `uv` managed Python 3.12 because project requires `>=3.12,<3.13`. [VERIFIED: shell `python3 --version`; VERIFIED: pyproject.toml] |
| `jq` | optional CLI JSON inspection | yes | 1.7.1 | Python JSON assertions. [VERIFIED: shell `jq --version`] |

**Missing dependencies with no fallback:** None for planning; real Qdrant service is not needed for unit tests. [VERIFIED: environment audit]

**Missing dependencies with fallback:** Qdrant CLI/server binary is absent; use Docker or qdrant-client local mode/fakes. [VERIFIED: environment audit; CITED: qdrant-client README]

## Testing Strategy

- Add `tests/test_embedding_provider.py` for deterministic provider, provider metadata, dimension validation, and provider failure errors. [ASSUMED]
- Add `tests/test_qdrant_indexing.py` with fake repository and optionally `QdrantClient(":memory:")` for create/upsert/payload mapping. [CITED: qdrant-client README]
- Add `tests/test_bm25_indexing.py` for jieba tokenization, TCM dictionary terms, `bm25s` save/load, and document count. [CITED: bm25s README]
- Add `tests/test_index_lifecycle.py` for build status transitions, validation failure, activation success, old active retention after failure. [VERIFIED: IDX-02, STAT-04]
- Add `tests/test_status_api.py` only after FastAPI is added; test no active index, active ready, last error, and Java-friendly JSON fields. [VERIFIED: STAT-01, STAT-02]
- Keep full verification command aligned with existing pattern: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest ... -q` plus `ruff check`. [VERIFIED: Phase 1 summaries]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no for Phase 2 local/status MVP | No auth designed yet; do not expose write/rebuild endpoints publicly. [VERIFIED: local demo scope] |
| V3 Session Management | no | No sessions. [VERIFIED: Phase 2 endpoint scope] |
| V4 Access Control | yes, operational surface | Keep rebuild CLI local; if HTTP rebuild is added later, require auth before public exposure. [ASSUMED] |
| V5 Input Validation | yes | Pydantic schemas and Path validation for CLI/API inputs. [VERIFIED: current Pydantic usage] |
| V6 Cryptography | no direct crypto | Do not implement custom crypto. [ASSUMED] |
| V10 Server-Side Request Forgery | low/conditional | Embedding provider URLs should come from config, not request payload. [ASSUMED] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Operator passes untrusted path | Tampering/Information Disclosure | Restrict CLI docs to local paths; avoid printing raw clinical-like row text. [VERIFIED: Phase 1 CLI logging decision] |
| Provider key or endpoint leaks in status | Information Disclosure | Status returns provider/model identifiers, not API keys or raw config secrets. [ASSUMED] |
| Partial/stale index served as fresh | Tampering/Repudiation | Persist build status, last_error, active_version, and validation counts. [VERIFIED: STAT-04] |
| Public rebuild endpoint triggers expensive model calls | Denial of Service | Prefer CLI rebuild in Phase 2; keep HTTP status read-only. [ASSUMED] |

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` - phase scope, requirements, constraints, known blockers. [VERIFIED: file read]
- `AGENTS.md` - project stack, scope, safety, GSD workflow constraints. [VERIFIED: file read]
- `.planning/phases/01-local-data-contract-and-ingestion/01-VERIFICATION.md` and `01-*-SUMMARY.md` - Phase 1 actual behavior and verification. [VERIFIED: file read]
- `pyproject.toml`, `src/zyfangji_retrieval/...`, `tests/test_local_persistence.py` - current dependencies and code boundaries. [VERIFIED: file read]
- PyPI JSON metadata on 2026-06-14 for package versions and upload timestamps. [VERIFIED: PyPI JSON]

### Primary Documentation (HIGH confidence)

- https://github.com/qdrant/qdrant-client - local mode, create/upsert examples, server connection. [CITED]
- https://qdrant.tech/documentation/concepts/collections/ - collections, named/sparse vectors, collection aliases. [CITED]
- https://github.com/xhluca/bm25s - tokenize/index/retrieve/save/load BM25 examples. [CITED]
- https://huggingface.co/BAAI/bge-m3 - BGE-M3 dimension, multilingual/dense/sparse/multi-vector model capabilities. [CITED]

### Secondary (MEDIUM confidence)

- Existing stack recommendation embedded in `AGENTS.md` - useful direction but still verified against current `pyproject.toml` and PyPI where Phase 2 dependencies are concerned. [VERIFIED: AGENTS.md, PyPI JSON]

### Tertiary (LOW confidence)

- Specific new file names and exact readiness status-code convention are planning recommendations, not existing project facts. [ASSUMED]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - versions verified through PyPI JSON and current `pyproject.toml`; Qdrant/BM25 behavior checked against official READMEs/docs. [VERIFIED: PyPI JSON; CITED docs]
- Architecture: HIGH - lifecycle requirements are explicit, and Qdrant aliases plus SQLite active state directly address version activation. [VERIFIED: REQUIREMENTS.md; CITED: Qdrant docs]
- Pitfalls: MEDIUM-HIGH - stale/partial/provider failures are explicitly required; tokenization-quality pitfalls are partly assumed from Chinese retrieval domain. [VERIFIED: STAT-04; ASSUMED]
- Testing: HIGH - current repo uses pytest/ruff with temp uv environment; external service tests can be isolated via fake/local client. [VERIFIED: Phase 1 summaries; CITED: qdrant-client README]

**Research date:** 2026-06-14  
**Valid until:** 2026-07-14 for project architecture; 2026-06-21 for package version currentness.
