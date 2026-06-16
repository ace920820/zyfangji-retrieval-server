# Reviewer Demo Guide

## Demo Modes

- Offline mode runs deterministic local sample retrieval without Qdrant, BGE-M3, reranker, network, or a running server.
- Live mode posts smoke fixture requests to `/api/search` on a running service.

## Offline Smoke Demo

```bash
uv run python scripts/demo_smoke.py --mode offline --limit 2
```

## Live API Demo

```bash
uv run python scripts/demo_smoke.py --mode live --base-url http://127.0.0.1:8000
```

## Sample Data Import

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
```

## Index Rebuild

```bash
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
```

## Start the API

```bash
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

## Run a Search

```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"main_symptom":"头痛","symptoms":["发热","恶风"],"pulse":"脉浮紧","topk":5}'
```

## Run Latency Check

```bash
uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode live --base-url http://127.0.0.1:8000
```

## How to Read Results Safely

Demo results are retrieval references for physician review, not diagnosis, medical advice, or autonomous prescription.

Scores are ranking/reference signals, not medical confidence.

Review formula names, source article, evidence fields, contraindication fields, warning codes, and score semantics together.

## Manual Review Checklist

- Open `/docs` in a browser and inspect `/api/search`, `/status`, `/health/live`, and `/health/ready`.
- Confirm import and rebuild are run through CLI commands.
- Run the offline smoke demo.
- Run the live API demo only after the service is started.
- Run the live latency command only when Qdrant, embedding, and reranker runtime are configured.

## Troubleshooting

- `embedding_provider_unavailable`: configure `ZYFANGJI_EMBEDDING_ENDPOINT_URL` or use offline demo mode.
- `reranker_unavailable`: confirm BGE-Reranker-v2-m3 runtime/provider availability or adjust reranker settings for demo mode.
- `index_not_ready`: import the workbook and run `index-rebuild --activate`.

