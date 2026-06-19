# zyfangji-retrieval

面向中医方剂检索 MVP 的检索服务。系统只做检索，不做聊天、诊断或自动处方。

## 这个服务做什么

服务读取《伤寒论》样例 Excel，导入本地元数据，构建 BM25 和向量检索索引，并通过 HTTP API 返回带典籍依据的方剂排序结果，供医生或业务后端审核使用。

## v1 不做什么

v1 不做聊天机器人，不做自动诊断，不做自动处方，不直连客户 MySQL 同步，也不提供后台管理系统。

## 快速开始

这组命令适合本地开发和确定性验证。正式接入 SiliconFlow 的 BGE-M3 embedding、Qdrant 和 rerank 时，请看下面的“正式运行流程”。

1. 安装依赖。
   ```bash
   uv sync
   ```

2. 导入样例 Excel。
   ```bash
   uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
   ```

3. 重建本地索引。
   ```bash
   uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
   ```

4. 启动 API。
   ```bash
   uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
   ```

## 导入和索引样例数据

v1 中，导入和重建索引是 CLI-only operator workflows in v1，没有 HTTP 导入或重建接口。

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run zyfangji-retrieval index-status --db-path var/metadata/knowledge.db
```

## 启动 API

```bash
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

OpenAPI 文档地址是 `/docs` 和 `/openapi.json`。OpenAPI is available at /docs and /openapi.json.

## 正式运行流程

这组流程用于真实接入 SiliconFlow BGE-M3 embedding、Qdrant 向量库和 SiliconFlow rerank，而不是 offline deterministic demo。

### 1. 配置环境变量

复制示例文件：

```bash
cp .env.example .env
```

在 `.env` 里填入真实 SiliconFlow API key：

```dotenv
ZYFANGJI_EMBEDDING_API_KEY=sk-your-real-siliconflow-api-key
ZYFANGJI_RERANKER_API_KEY=sk-your-real-siliconflow-api-key
```

如果你在宿主机直接用 `uv` / `uvicorn` 运行 API，Qdrant 地址应为：

```dotenv
ZYFANGJI_QDRANT_URL=http://localhost:6333
```

如果 API 也跑在 Docker Compose 容器里，Qdrant 地址应为：

```dotenv
ZYFANGJI_QDRANT_URL=http://qdrant:6333
```

### 2. 启动 Docker 和 Qdrant

如果 macOS 上 Docker 使用 Colima，先启动 Colima：

```bash
colima start
```

再启动 Qdrant：

```bash
docker compose up -d qdrant
docker compose ps
curl http://127.0.0.1:6333/healthz
```

如果拉取 `qdrant/qdrant:v1.18.2` 超时，可以先尝试 GHCR 官方镜像并打成本地 tag：

```bash
docker pull ghcr.io/qdrant/qdrant/qdrant:v1.18.2
docker tag ghcr.io/qdrant/qdrant/qdrant:v1.18.2 qdrant/qdrant:v1.18.2
docker compose up -d qdrant
```

也可以为 Colima 配置可用的 Docker registry mirror 后再重试拉取。

### 3. 导入源数据

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
```

### 4. 重建检索索引

目标正式命令是：

```bash
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run zyfangji-retrieval index-status --db-path var/metadata/knowledge.db
```

重要：默认 `index-rebuild` 会读取 `.env` 中的 embedding provider 配置，并连接 `ZYFANGJI_QDRANT_URL` 指向的 Qdrant 服务。使用 SiliconFlow 时，这一步会调用真实 BGE-M3 embedding 接口并把向量写入外部 Qdrant。

如果只想做离线确定性验证，不调用 SiliconFlow，也不写外部 Qdrant，可以显式加 `--local-demo`：

```bash
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate --local-demo
```

因为 embedding provider、向量维度和 Qdrant collection 内容都是索引状态的一部分，从 deterministic embedding 切换到真实 BGE-M3 后必须 fresh rebuild，不要复用旧 demo index 做 live testing。

### 5. 启动 API

宿主机本地运行：

```bash
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

Docker Compose 运行 API：

```bash
docker compose up --build api
```

检查服务状态：

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/status
```

### 6. 执行 live 查询

交互式 CLI 连接 live API：

```bash
uv run zyfangji-retrieval demo interactive --mode live --base-url http://127.0.0.1:8000 --topk 5
```

运行 live smoke demo：

```bash
uv run python scripts/demo_smoke.py --mode live --base-url http://127.0.0.1:8000
```

直接调用 HTTP API：

```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"main_symptom":"头痛","symptoms":["发热","恶风"],"pulse":"脉浮紧","topk":5}'
```

### 常见问题

- `.colima` 下 Docker socket 不存在：运行 `colima start`，再用 `docker info` 确认。
- Qdrant 镜像拉取超时：尝试 GHCR 镜像、Docker registry mirror，或在可访问 Docker Hub 的网络下重试。
- Qdrant 不可用：确认 `docker compose ps` 显示 `qdrant` 正在运行，并且 `curl http://127.0.0.1:6333/healthz` 成功。
- `embedding_provider_unavailable`：检查 `ZYFANGJI_EMBEDDING_ENDPOINT_URL` 和 `ZYFANGJI_EMBEDDING_API_KEY`。
- `reranker_unavailable`：检查 `ZYFANGJI_RERANKER_ENDPOINT_URL`、`ZYFANGJI_RERANKER_API_KEY` 和 `ZYFANGJI_RERANKER_PROVIDER=silicon`。
- `index_not_ready`：先导入源数据，重建索引，再确认 `index-status` 有 active index。

## API 和集成文档

- [docs/API.md](docs/API.md)
- [docs/DEMO.md](docs/DEMO.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)
- [.env.example](.env.example)

## Demo 和验证

- 离线 reviewer demo：`uv run python scripts/demo_smoke.py --mode offline --limit 2`
- 延迟检查：`uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline`
- 示例客户端：`scripts/demo_smoke.py`

## 配置

所有 `ZYFANGJI_` 配置见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) 和 [.env.example](.env.example)。

## 安全和隐私

检索分数不是 medical confidence, diagnosis probability, or prescription certainty；它只用于排序和参考展示。

不要记录原始患者表现文本、provider API key 或完整 provider 错误响应。

## 项目结构

- `src/zyfangji_retrieval/` - API、CLI、导入、索引、检索和持久化代码
- `tests/` - 合同、回归和 smoke 测试
- `scripts/` - demo 和延迟检查脚本
- `docs/` - API、demo 和部署文档
