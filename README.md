# zyfangji-retrieval

Retrieval-only service for the Zhongyi formula search MVP.

## What This Service Does

It imports the provided Shanghanlun workbook, builds local retrieval indexes, and serves ranked formula results with evidence for physician review.

## What Is Out of Scope in v1

No chat, no autonomous diagnosis, no autonomous prescription, no customer MySQL sync, and no admin console in v1.

## Quick Start

1. Install dependencies.
   ```bash
   uv sync
   ```
2. Import the sample workbook.
   ```bash
   uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
   ```
3. Rebuild the local index.
   ```bash
   uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
   ```
4. Start the API.
   ```bash
   uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
   ```

## Import and Index the Sample Workbook

Import and rebuild are CLI-only operator workflows in v1.

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run zyfangji-retrieval index-status --db-path var/metadata/knowledge.db
```

## Run the API

```bash
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

OpenAPI is available at /docs and /openapi.json.

## API and Integration Docs

- [docs/API.md](docs/API.md)
- [docs/DEMO.md](docs/DEMO.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)
- [.env.example](.env.example)

## Demo and Validation

- Offline reviewer demo: `uv run python scripts/demo_smoke.py --mode offline --limit 2`
- Latency check: `uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline`
- Sample client: `scripts/demo_smoke.py`

## Configuration

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [.env.example](.env.example) for all `ZYFANGJI_` settings.

## Safety and Privacy Notes

Retrieval scores are not medical confidence, diagnosis probability, or prescription certainty.

Do not log raw patient presentation text, provider API keys, or full provider error bodies.

## Project Layout

- `src/zyfangji_retrieval/` - API, CLI, ingestion, indexing, search, and persistence code
- `tests/` - contract, regression, and smoke tests
- `scripts/` - demo and latency helpers
- `docs/` - API, demo, and deployment guides
