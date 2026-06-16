---
phase: 05
slug: documentation-and-demo-delivery
status: complete
created: 2026-06-16
source: gsd-plan-phase
---

# Phase 05 - Research

> Planning research for documentation, Java integration examples, demo flow, and deployment/runbook packaging.

## Phase Goal

Reviewers and the Java/backend/frontend team can run the service, inspect API contracts, import sample data, and execute search flows without shell-only tribal knowledge.

## Requirement IDs

- DOC-01: Publish OpenAPI/Swagger documentation for import, search, status, and health endpoints.
- DOC-02: Include Java-backend integration examples for import/status/search flows.
- DOC-03: Document required environment variables, BGE-M3/reranker configuration, startup steps, and Docker Compose commands.
- DOC-04: Document local-file data assumptions, score semantics, formula-code mapping behavior, privacy-conscious logging, and out-of-scope medical-chat behavior.
- DOC-05: Provide a minimal demo flow or sample client where a reviewer can import the sample data and run a symptom search.

## Existing Surfaces

| Surface | Current State | Planning Implication |
|---------|---------------|----------------------|
| FastAPI app | `src/zyfangji_retrieval/api/app.py` creates `FastAPI(title=settings.api_title)` and includes status/search routers. | OpenAPI is already available at `/docs` and `/openapi.json` when the API runs. |
| HTTP routes | `GET /health/live`, `GET /health/ready`, `GET /status`, `POST /api/search`. | Document exactly these routes; do not invent import/rebuild HTTP routes. |
| Search contract | `PatientSearchRequest` fields are `main_symptom`, `symptoms`, `tongue`, `pulse`, `syndrome`, `topk`; response has `query`, `results`, `warnings`, `metadata`, `score_semantics`. | Java examples should use the real request/response shape and current error envelope. |
| CLI | `inspect-workbook`, `import-excel`, `rebuild-source`, `index-rebuild`, `index-validate`, `index-status`. | Import/rebuild are currently operator CLI workflows, not HTTP workflows. |
| Config | `AppSettings` uses `ZYFANGJI_` env vars for DB, Qdrant, embedding, BM25, search, fusion, reranker, and API title. | README and `.env.example` must list every supported setting. |
| Smoke/latency | `tests/fixtures/smoke_queries.json` and `scripts/search_latency.py` exist. | Reuse these as demo validation and sample query sources. |
| README | Stale; only describes Phase 1. | Replace with MVP runbook and links to detailed docs. |
| Docker | No `Dockerfile` or Compose file exists. | Phase 5 must add packaging docs/files if Docker Compose remains a requirement. |

## Key Discovery: Import Is CLI-Only

Roadmap success criteria mention OpenAPI/Swagger docs covering import/search/status/health. The implementation currently exposes HTTP only for search, status, and health. Import and rebuild exist as Typer CLI commands.

Phase 5 should resolve this by documenting:

- OpenAPI/Swagger covers the actual HTTP API: `/api/search`, `/status`, `/health/live`, `/health/ready`.
- Import/rebuild are operator CLI workflows for v1:
  - `uv run zyfangji-retrieval import-excel ...`
  - `uv run zyfangji-retrieval index-rebuild ...`
  - `uv run zyfangji-retrieval index-status ...`
- Do not claim a HTTP import endpoint exists unless a later plan explicitly implements one. For this phase, keep scope documentation-first and retrieval-only.

## Documentation Gaps

| Gap | Requirement | Needed Artifact |
|-----|-------------|-----------------|
| README still describes only Phase 1 | DOC-01, DOC-03, DOC-04, DOC-05 | Replace with install/run/demo/API overview. |
| Java/backend examples missing | DOC-02 | Add docs with Java 11+ `HttpClient` and curl examples for status/health/search; document import as CLI/operator step. |
| Config table missing | DOC-03 | Add `.env.example` and docs table covering all `ZYFANGJI_` settings. |
| OpenAPI route contract not regression-tested as documentation surface | DOC-01 | Add a docs contract test for `create_app().openapi()` paths and schemas. |
| Demo flow not packaged | DOC-05 | Add a reviewer-facing script/client that can print safe smoke search output or instructions around existing smoke fixture. |
| Privacy/safety/out-of-scope notes absent from public docs | DOC-04 | Add explicit score semantics, no diagnosis/prescribing, no chat/admin/NER/MySQL sync, and logging guidance. |
| Docker Compose missing | DOC-03 | Add `Dockerfile`/`docker-compose.yml` or document why external provider services are required; for v1, package API + Qdrant and keep models provider-configured. |

## Demo/Deployment Plan Notes

Recommended reviewer flow:

1. `uv sync`
2. `uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db`
3. `uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate`
4. Start API with explicit demo-safe settings:
   - deterministic local smoke mode for offline docs/tests, or
   - configured `ZYFANGJI_EMBEDDING_ENDPOINT_URL` and reranker settings for live provider mode.
5. Open `/docs`.
6. Check `/status` and `/health/ready`.
7. Run `/api/search` with sample symptom payload.
8. Run `scripts/search_latency.py --mode live --base-url http://127.0.0.1:8000` only when the live service is running.

Docker packaging notes:

- Compose should include Qdrant and the API service.
- Persist `var/metadata`, `var/indexes`, and Qdrant storage.
- Do not containerize heavy local BGE/reranker models unless target hardware is confirmed.
- Document provider/reranker environment variables rather than hiding them.

## Risks and Threats

| Risk | Impact | Planning Mitigation |
|------|--------|---------------------|
| Documenting nonexistent HTTP import endpoint | Java team follows wrong integration path. | Explicitly distinguish HTTP API from CLI operator import/rebuild. |
| Default live settings require BGE endpoint/reranker runtime | Demo search can fail with provider errors. | Docs must show both provider-configured mode and deterministic/offline validation commands. |
| Java examples drift from schema | Integration errors. | Add tests/grep checks for examples and OpenAPI paths. |
| Demo output uses diagnosis/prescription language | Medical safety boundary regression. | Use wording: retrieval result, evidence, ranking signal; forbid confidence/diagnosis/prescription certainty language. |
| Patient text/API keys appear in logs/examples | Privacy risk. | Document logging policy and redact API keys/sample patient details in scripts. |
| Scope creep into admin/chat/NER/MySQL sync | Delivery delay. | Out-of-scope section must be prominent in README/docs. |

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.0 |
| Config file | `pyproject.toml` |
| Lint command | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts` |
| Focused docs command | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_documentation_contract.py -q` |
| Demo command | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/demo_smoke.py --queries tests/fixtures/smoke_queries.json --mode offline` |

Suggested validation tests:

- DOC-01: `create_app().openapi()` includes `/api/search`, `/status`, `/health/live`, `/health/ready`; docs do not claim a `/api/import` route.
- DOC-02: README/docs include Java `HttpClient` examples using current fields: `main_symptom`, `symptoms`, `tongue`, `pulse`, `syndrome`, `topk`, `query`, `results`, `warnings`, `metadata`, `score_semantics`.
- DOC-03: `.env.example` or config docs mention every `AppSettings` field as a `ZYFANGJI_` variable.
- DOC-04: Docs contain local-file assumptions, score semantics, formula mapping behavior, privacy logging, and out-of-scope admin/chat/NER/MySQL sync.
- DOC-05: Demo script/sample client validates request payloads through `PatientSearchRequest`, reads smoke fixture, and prints safe evidence-focused output without diagnosis/advice/prescribing claims.

Manual validation:

- Open `/docs` in browser once API is running.
- Follow the clean checkout runbook to import/rebuild/start/status/search.
- Run live latency only when provider/Qdrant/reranker runtime is configured.

## Suggested Plan Split

| Plan | Name | Scope |
|------|------|-------|
| 05-01 | API docs and Java integration contract | README/API docs, OpenAPI route contract test, Java/curl examples, import CLI vs HTTP API clarification. |
| 05-02 | Reviewer demo flow and sample client | Smoke demo script, demo guide, safe output and fixture-backed tests. |
| 05-03 | Deployment/runbook packaging | `.env.example`, Dockerfile/Compose, provider/reranker config docs, privacy/out-of-scope checklist, final validation commands. |

## Sources

- `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` — Phase 5 goal and DOC requirements.
- `.planning/phases/04-quality-safety-and-performance-validation/04-VERIFICATION.md` and `04-HUMAN-UAT.md` — pending live latency/domain review boundaries.
- `README.md` — stale Phase 1-only documentation.
- `src/zyfangji_retrieval/api/app.py`, `src/zyfangji_retrieval/api/routes/status.py`, `src/zyfangji_retrieval/api/routes/search.py` — real HTTP route surface.
- `src/zyfangji_retrieval/cli.py` — import/rebuild/status CLI surface.
- `src/zyfangji_retrieval/config.py` — environment settings.
- `tests/test_search_api.py`, `tests/test_status_api.py`, `tests/test_index_lifecycle.py` — existing contract behaviors.
- `tests/fixtures/smoke_queries.json`, `scripts/search_latency.py` — smoke/demo validation assets.

## RESEARCH COMPLETE
