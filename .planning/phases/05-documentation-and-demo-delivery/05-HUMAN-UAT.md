---
status: partial
phase: 05-documentation-and-demo-delivery
source: [05-VERIFICATION.md]
started: 2026-06-16T22:20:00+08:00
updated: 2026-06-16T22:20:00+08:00
---

## Current Test

[awaiting human testing]

## Tests

### 1. Open Swagger/OpenAPI in the running API

command:

```bash
uvicorn zyfangji_retrieval.api.app:app --host 0.0.0.0 --port 8000
```

then open:

```text
http://127.0.0.1:8000/docs
```

expected: Swagger shows `/api/search`, `/status`, `/health/live`, and `/health/ready`; import/rebuild are not shown as HTTP endpoints.
result: [pending]

### 2. Follow live demo runbook with provider/runtime configuration

command:

```bash
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run python scripts/demo_smoke.py --mode live --base-url http://127.0.0.1:8000
```

expected: live demo returns ranked formula references with source articles, warnings, pipeline status, and score semantics.
result: [pending]

### 3. Review Docker Compose packaging on target machine

command:

```bash
cp .env.example .env
docker compose up --build
```

expected: Qdrant and API containers start, `/health/live` responds, and provider-specific failures are explicit if BGE/reranker endpoints are not configured.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

No repository documentation/test gaps remain. Human UAT is limited to live browser/provider/Docker environment confirmation.
