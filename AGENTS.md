<!-- GSD:project-start source:PROJECT.md -->
## Project

**中医方剂检索系统**

中医方剂检索系统是一个面向医生的轻量级方剂检索服务。医生或业务后端提交患者门诊采集信息，包括症状、舌诊、脉象、望闻问切描述等，系统基于《伤寒论》等结构化中医典籍资料返回匹配度靠前的方剂和依据条目。

一期目标是用现有《伤寒论》Excel 样例数据做出可演示的检索服务和接口文档，让业务后端能够导入/更新知识数据，并通过检索接口获得可展示的推荐结果。它不是一期的中医聊天机器人，也不负责生成诊疗建议。

**Core Value:** 医生输入患者症状后，系统必须能稳定返回有典籍依据、排序合理、可回连业务方剂库的推荐方剂列表。

### Constraints

- **Timeline**: 两到三周内交付样例服务或页面 — 客户希望尽快看到效果。
- **Scope**: 一期只做检索，不做对话生成 — 避免把搜索引擎式需求误做成聊天系统。
- **Data Source**: 业务方维护 MySQL/二维表，检索服务构建独立索引 — 检索不应实时依赖业务库扫描。
- **Data Shape**: 先适配《伤寒论》Excel 的 22 列结构 — 后续 200 本书字段统一性尚未确认。
- **Integration**: 检索服务需要面向 Java 后端提供稳定 HTTP API 和接口文档 — 前端展示由需求方团队对接。
- **Scoring**: 匹配分可返回但主要用于排序展示 — 语义检索分数绝对值不应被解释为医学置信度。
- **Safety**: 返回内容应保留典籍依据、禁忌和西医优先建议字段 — 医疗场景需要让医生看到依据和风险提示。
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommendation
## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Retrieval service runtime | Best ecosystem for embeddings, vector DB clients, BM25 tooling, Excel parsing, and ML rerankers. Use 3.12 for mature package compatibility; avoid jumping to 3.13 if model packages lag. Confidence: HIGH. |
| FastAPI | 0.136.3 | REST API for Java backend and management endpoints | Current official release as of 2026-05-23. Gives OpenAPI docs for backend integration, Pydantic validation, async HTTP clients, and simple deployment. Confidence: HIGH. |
| Pydantic | 2.13.4 | Request/response schemas and config validation | FastAPI-native validation layer; use explicit schemas for patient symptom query, import job status, and retrieval result payloads. Confidence: HIGH. |
| Uvicorn | 0.49.0 | ASGI server | Standard FastAPI runtime. For demo, one Uvicorn process is enough; for production, run under Docker/systemd or behind Nginx. Confidence: HIGH. |
| Qdrant server | 1.18.2 | Vector database and hybrid retrieval store | Official Qdrant release current as of 2026-06-04. Supports dense vectors, sparse vectors, payload filters, named vectors, and hybrid query patterns via prefetch/fusion. Runs easily in Docker for a demo and scales to the likely 200-book expansion. Confidence: HIGH. |
| qdrant-client | 1.18.0 | Python client for Qdrant | Current PyPI client. Use for collection creation, upsert/delete, snapshots, index status, and query APIs. Confidence: HIGH. |
| pandas | 3.0.3 | Structured Excel/table ingestion | Fastest path to normalize the existing `.xlsx` sheet into validated records; handles future CSV/export data well. Confidence: HIGH. |
| openpyxl | 3.1.5 | Excel engine for `.xlsx` files | Required practical backend for pandas Excel ingestion. Current PyPI version remains 3.1.5. Confidence: HIGH. |
### Retrieval and Ranking
| Library / Service | Version | Purpose | When to Use |
|-------------------|---------|---------|-------------|
| Qdrant named dense+sparse vectors | Qdrant 1.18.2 | Primary retrieval index | Use one collection with payload metadata, a dense vector for semantic matching, and either Qdrant sparse vectors or local BM25 candidates for lexical matching. Confidence: HIGH. |
| bm25s | 0.3.9 | In-process BM25 lexical retrieval | Use in v1 as a transparent lexical baseline and fallback. It is simple, fast enough for thousands to hundreds of thousands of records, and avoids running Elasticsearch/OpenSearch for the demo. Confidence: MEDIUM-HIGH. |
| jieba | 0.42.1 | Chinese tokenization for BM25 fields | Use for Chinese symptom, tongue, pulse, disease, pattern, formula, and alias fields. Keep a project dictionary for TCM terms such as "太阳病", "麻黄汤", "脉浮紧". Confidence: MEDIUM. |
| External embedding API | Provider-specific | Dense semantic vectors | Recommended for v1 demo to avoid GPU/model packaging work. Choose a Chinese-capable embedding model from the customer-approved provider, then pin dimensions in config. Confidence: MEDIUM until provider is chosen. |
| OpenAI embeddings | `text-embedding-3-small` or newer official embedding model | Low-friction cloud embedding option | Use if cross-border/network/account constraints are acceptable. Good API ergonomics, but not the default recommendation for a China-facing medical demo unless the customer already approves it. Confidence: MEDIUM. |
| BAAI bge-m3 | model revision pinned from Hugging Face/ModelScope | Local or private dense + sparse embedding option | Use if data/network constraints require local inference or China-hosted model assets. Strong multilingual/Chinese retrieval reputation, but packaging Torch/Transformers adds ops cost. Confidence: MEDIUM-HIGH for capability, MEDIUM for schedule fit. |
| Optional reranker API | Provider-specific | Second-stage precision improvement | Add after baseline hybrid retrieval works. Rerank top 30-50 candidates down to topK. Keep it optional because it adds latency, cost, and provider dependency. Confidence: MEDIUM. |
| BAAI bge-reranker-v2-m3 | model revision pinned from Hugging Face/ModelScope | Local cross-encoder reranking | Use only if GPU/CPU latency is acceptable. Good fit for Chinese/medical-ish text pairs, but risky for a 2-week demo unless deployment host is known. Confidence: MEDIUM. |
### API and Service Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | 2.14.1 | Environment-based config | Use for API keys, Qdrant URL, collection name, embedding provider, rerank flag, and score blending weights. Confidence: HIGH. |
| httpx | 0.28.1 | Async outbound HTTP client | Use for embedding/reranker provider calls and Java backend callbacks if needed. Confidence: HIGH. |
| orjson | 3.11.9 | Fast JSON serialization | Use as FastAPI response serializer once payloads include full source rows. Confidence: MEDIUM-HIGH. |
| Typer | 0.26.7 | CLI for local import/rebuild scripts | Use for `import-excel`, `rebuild-index`, `smoke-query`, and admin maintenance commands. Confidence: HIGH. |
| python-multipart | current | File upload support | Use only if management API accepts uploaded Excel files. If Java backend passes table exports or file paths, skip it. Confidence: MEDIUM. |
| SQLAlchemy | 2.x | Optional MySQL pull adapter | Use only if v1 must read directly from customer MySQL. Prefer file/import API first to keep demo decoupled. Confidence: MEDIUM. |
| PyMySQL or mysqlclient | current | Optional MySQL driver | Add only with SQLAlchemy adapter. Avoid making MySQL a hard runtime dependency unless the integration contract requires it. Confidence: MEDIUM. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| uv | 0.11.21 | Python dependency/environment manager | Use `pyproject.toml` + lockfile for reproducible demo deployment. Faster and less fragile than ad hoc pip commands. Confidence: HIGH. |
| Docker Compose | current Docker Engine | Local/demo orchestration | Run API + Qdrant + optional Nginx. Do not containerize heavyweight local models unless deployment host resources are confirmed. Confidence: HIGH. |
| ruff | 0.15.17 | Linting and formatting | One tool for formatting/import/lint checks; good enough for small service. Confidence: HIGH. |
| pytest | 9.1.0 | Unit/API tests | Use for ingestion normalization, scoring fusion, and endpoint contract tests. Confidence: HIGH. |
| pytest-asyncio | current | Async FastAPI/provider tests | Use if embedding/rerank clients are async. Confidence: MEDIUM. |
| httpx ASGI transport / TestClient | current | API contract tests | Validate Java-facing JSON schemas and error shapes. Confidence: HIGH. |
## Installation
# Runtime
# Optional provider clients; add only when selected
# Dev dependencies
## Prescribed Retrieval Pipeline
| Signal | Default Weight | Rationale |
|--------|----------------|-----------|
| Dense semantic rank | 0.55 | Handles synonymy and incomplete symptom phrasing. |
| BM25 lexical rank | 0.35 | Keeps exact TCM terms, formula names, tongue/pulse terms, and original clauses influential. |
| Structured field boosts | 0.10 | Boost if query explicitly includes tongue/pulse/body part/formula/pattern matches. |
| Reranker | Off by default | Enable only after baseline evaluation shows ordering problems and latency budget is acceptable. |
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI microservice | Spring Boot retrieval service | Use Spring only if the team insists on one Java monolith. For vector/embedding/BM25 work, Python is materially faster to build and easier to integrate with ML libraries. |
| Qdrant | Milvus | Use Milvus when the roadmap demands very large distributed vector infrastructure. For a 2-3 week demo and likely modest corpus, Qdrant is simpler to operate. |
| Qdrant | Elasticsearch/OpenSearch vector search | Use Elasticsearch/OpenSearch if the organization already runs it and needs advanced keyword search/admin tooling. Otherwise it is heavier than needed for this service. |
| `bm25s` + jieba | Elasticsearch BM25 | Use Elasticsearch if the BM25 layer becomes a separately managed search product. For v1, in-process BM25 is enough and easier to tune. |
| External embedding API | Local bge-m3 | Use local bge-m3 when API/network/privacy constraints block cloud embeddings. It is more work to package and benchmark. |
| Optional reranker | Always-on reranker | Use always-on only after measuring latency and quality. V1 needs a reliable baseline first. |
| Hand-written retrieval pipeline | LangChain/LlamaIndex | Use LangChain/LlamaIndex only if v2 becomes a multi-tool RAG/chat workflow. V1 is structured ingestion + search API; framework abstractions add moving parts without much benefit. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Chatbot/RAG agent framework as the core | V1 is not a chat product and does not need prompt chains, memory, tool agents, or generative answers. It needs deterministic ranked rows. | FastAPI service with explicit ingestion/retrieval modules. |
| Direct SQL `LIKE` search over MySQL | Poor synonym handling, no semantic match, weak ranking, and poor isolation from business DB load. | Qdrant dense retrieval + BM25 lexical retrieval. |
| MySQL as the only source of truth for retrieval state | Rebuilding and querying embeddings directly from business tables couples search behavior to OLTP schema and update timing. | Import/sync from Excel/MySQL into an independent retrieval index. |
| FAISS-only local vector files for the deployed service | Fine for notebooks, but weaker for API operations: payload filtering, deletes, snapshots, observability, and future scaling. | Qdrant Docker service. |
| Chroma for production demo API | Convenient for prototypes, but Qdrant has stronger production operations and hybrid/vector DB ergonomics. | Qdrant. |
| Milvus/Zilliz for v1 | More operational surface than needed for ~1k rows and a 2-3 week demo. | Qdrant; revisit Milvus only if corpus and ops requirements grow substantially. |
| Elasticsearch/OpenSearch in v1 unless already available | Adds JVM ops, index mapping complexity, and cluster management for a small corpus. | `bm25s` + Qdrant. |
| Local LLM deployment | Explicitly out of scope and high deployment risk. | Cloud embedding/rerank APIs; local embedding only if necessary. |
| Treating similarity score as diagnostic probability | Vector scores are dense and relative; the conversation already noted absolute scores can mislead users. | Return rank score with explanatory naming such as `match_score`, and include source evidence fields. |
## Stack Patterns by Variant
- FastAPI + Qdrant Docker + pandas/openpyxl + `bm25s`/jieba + external embedding API.
- Reranker disabled or provider-backed feature flag.
- Best because it minimizes deployment risk and proves the product value quickly.
- Keep the same service architecture.
- Swap embedding provider to a customer-approved Chinese cloud model provider or ModelScope-hosted/self-hosted bge-m3.
- Keep provider behind an `EmbeddingClient` interface so roadmap phases do not depend on one vendor.
- Use bge-m3 locally through FlagEmbedding/sentence-transformers if host resources permit.
- If host resources are weak, ship BM25 + structured boosts first and mark semantic vectors as blocked by model provisioning.
- Keep Qdrant.
- Move ingestion to incremental sync jobs, add snapshot/backup automation, and store source documents/import jobs in PostgreSQL or MySQL.
- Consider Qdrant sparse vectors for unified hybrid indexing instead of separate local BM25 files.
- Add a field mapping layer before indexing.
- Store canonical fields plus source-specific payloads.
- Do not hard-code the 22-column Shanghanlun schema into retrieval APIs.
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.136.3 | Pydantic 2.13.4 | FastAPI has used Pydantic v2 for current releases; keep schemas on v2 idioms. |
| FastAPI 0.136.3 | Uvicorn 0.49.0 | Standard ASGI pairing. |
| Qdrant server 1.18.2 | qdrant-client 1.18.0 | Keep client/server close in minor version to avoid query API drift. |
| pandas 3.0.3 | openpyxl 3.1.5 | pandas reads `.xlsx` through openpyxl. Pin both to make Excel parsing reproducible. |
| FlagEmbedding 1.4.0 | sentence-transformers 5.5.1 / transformers 5.12.0 / torch 2.12.0 | Local model stack is the riskiest dependency area; test on target OS/GPU before committing to local inference. |
| bm25s 0.3.9 | jieba 0.42.1 | Tokenization quality depends more on a project dictionary than package version. |
## Confidence Assessment
| Recommendation | Confidence | Evidence / Rationale |
|----------------|------------|----------------------|
| FastAPI/Pydantic for API service | HIGH | Official FastAPI release currentness verified; strong fit for OpenAPI contract and Python retrieval stack. |
| Qdrant as vector DB | HIGH | Official GitHub latest release verified as v1.18.2 on 2026-06-04; Qdrant docs support hybrid query concepts including dense/sparse retrieval. |
| pandas/openpyxl for Excel ingestion | HIGH | Current PyPI versions verified; directly matches source data shape. |
| `bm25s` + jieba for v1 BM25 | MEDIUM-HIGH | Current PyPI versions verified; suitable for small corpus. Needs Chinese token dictionary tuning. |
| External embedding API for demo | MEDIUM | Strong schedule fit, but exact provider/model depends on customer account, region, and compliance constraints. |
| Local bge-m3 / bge-reranker-v2-m3 | MEDIUM | Models are widely used for multilingual retrieval/reranking and official model pages exist, but local deployment should be benchmarked on target hardware. |
| Avoid LangChain/LlamaIndex in v1 core | HIGH | Product is retrieval API, not agent/chat workflow; simpler explicit pipeline lowers delivery risk. |
## Sources
- Project context: `.planning/PROJECT.md` and `data/任如亮项目对话.txt` — verified v1 is retrieval-only, data starts from structured Excel, Java backend integration required, and local/private LLM deployment is out of scope.
- FastAPI official release notes: https://fastapi.tiangolo.com/release-notes/ — latest release verified as 0.136.3 on 2026-05-23. Confidence: HIGH.
- PyPI JSON/package metadata checks on 2026-06-14 — FastAPI 0.136.3, Pydantic 2.13.4, Uvicorn 0.49.0, qdrant-client 1.18.0, pandas 3.0.3, openpyxl 3.1.5, bm25s 0.3.9, FlagEmbedding 1.4.0, sentence-transformers 5.5.1, openai 2.41.1, ruff 0.15.17, pytest 9.1.0. Confidence: HIGH for package currentness.
- Qdrant GitHub releases API: https://api.github.com/repos/qdrant/qdrant/releases/latest — latest release verified as v1.18.2 published 2026-06-04. Confidence: HIGH.
- Qdrant hybrid query documentation: https://qdrant.tech/documentation/concepts/hybrid-queries/ — verified current support for hybrid/multi-stage query patterns. Confidence: HIGH.
- Qdrant sparse vector documentation: https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors — support for sparse vectors relevant to BM25/SPLADE-style hybrid retrieval. Confidence: HIGH.
- OpenAI embedding documentation: https://platform.openai.com/docs/guides/embeddings — verified official embedding API option, but region/provider suitability is project-specific. Confidence: MEDIUM.
- BAAI bge-m3 model page: https://huggingface.co/BAAI/bge-m3 — official model page for local multilingual retrieval option. Confidence: MEDIUM-HIGH.
- BAAI bge-reranker-v2-m3 model page: https://huggingface.co/BAAI/bge-reranker-v2-m3 — official model page for local reranking option. Confidence: MEDIUM.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
