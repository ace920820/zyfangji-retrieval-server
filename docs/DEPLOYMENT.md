# Deployment and Operations Runbook

## Runtime Components

- FastAPI service: `zyfangji_retrieval.api.app:app`
- Qdrant vector store
- SQLite metadata/index state under `var/metadata/knowledge.db`
- BM25 artifacts under `var/indexes/bm25`
- Optional external BGE-M3 embedding endpoint
- Optional BGE-Reranker-v2-m3 runtime/provider

## Environment Variables

Start from:

```bash
cp .env.example .env
```

Every supported `ZYFANGJI_` setting is listed in `.env.example`.

## Local uv Run

```bash
uv sync
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

## Docker Compose Run

```bash
docker compose up --build
```

The compose file starts Qdrant and the API service. It mounts `./var` for metadata/index artifacts and `./data` read-only for sample files.

## Provider and Reranker Configuration

Configure BGE-M3 through `ZYFANGJI_EMBEDDING_PROVIDER`, `ZYFANGJI_EMBEDDING_MODEL_ID`, `ZYFANGJI_EMBEDDING_ENDPOINT_URL`, `ZYFANGJI_EMBEDDING_API_KEY`, and `ZYFANGJI_EMBEDDING_TIMEOUT_SECONDS`.

Configure BGE-Reranker-v2-m3 through `ZYFANGJI_RERANKER_PROVIDER`, `ZYFANGJI_RERANKER_MODEL_ID`, and `ZYFANGJI_RERANKER_REQUIRED`.

Offline smoke and documentation validation commands do not require provider credentials.

## Import and Rebuild Workflow

Local Excel / local structured files are the v1 data source.

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run zyfangji-retrieval index-status --db-path var/metadata/knowledge.db
```

## Health and Status Checks

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/status
```

## Smoke, Latency, and Manual UAT

```bash
uv run python scripts/demo_smoke.py --mode offline --limit 2
uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline
```

Use live mode only when the API service is running:

```bash
uv run python scripts/demo_smoke.py --mode live --base-url http://127.0.0.1:8000
uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode live --base-url http://127.0.0.1:8000
```

## Privacy-Conscious Logging

Do not log raw patient presentation text, provider API keys, or full provider error bodies.

For demos, log request IDs, index versions, provider status, and high-level error codes instead of raw clinical text.

## Out of Scope for v1

No customer MySQL sync, admin console, chat UI, symptom NER, autonomous diagnosis, or autonomous prescription in v1.

## Troubleshooting

- Missing active index: run import and `index-rebuild --activate`.
- Provider unavailable: check `ZYFANGJI_EMBEDDING_ENDPOINT_URL` and provider credentials.
- Reranker unavailable: check reranker provider setting or runtime availability.
- Qdrant unavailable: confirm `ZYFANGJI_QDRANT_URL` and Docker Compose service health.

