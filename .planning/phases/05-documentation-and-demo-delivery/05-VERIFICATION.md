---
phase: 05-documentation-and-demo-delivery
verified: 2026-06-16T22:20:00+08:00
status: human_needed
score: 5/5 must-haves verified by repository automation
overrides_applied: 0
human_verification:
  - test: "Open `/docs` against a running API process"
    expected: "Swagger shows the real v1 HTTP routes and no import/rebuild HTTP endpoints"
    why_human: "Repository tests inspect OpenAPI programmatically; browser rendering requires a running local service"
  - test: "Run live demo flow against configured Qdrant, BGE-M3, and BGE-Reranker-v2-m3 runtime"
    expected: "Reviewer can import data, rebuild/activate index, start API, and run live demo smoke search"
    why_human: "Provider credentials, model runtime, Docker daemon, and target machine resources are environment-specific"
---

# Phase 5: Documentation and Demo Delivery Report

**Phase Goal:** Reviewers and the Java/backend/frontend team can run the service, inspect API contracts, import sample data, and execute search flows without shell-only tribal knowledge.
**Verified:** 2026-06-16T22:20:00+08:00
**Status:** human_needed

## Goal Achievement

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | OpenAPI/Swagger covers the real HTTP routes for search, status, and health. | VERIFIED / HUMAN CHECK | `tests/test_documentation_contract.py` asserts OpenAPI paths include `/api/search`, `/status`, `/health/live`, and `/health/ready`, and exclude import/rebuild HTTP routes. Browser rendering at `/docs` remains manual. |
| 2 | Environment variables, BGE-M3/reranker configuration, startup steps, and Docker Compose commands are documented. | VERIFIED | `.env.example`, `Dockerfile`, `docker-compose.yml`, and `docs/DEPLOYMENT.md` cover runtime configuration and Compose packaging. |
| 3 | Java-backend integration examples show status/search request and response flows, with CLI import clarification. | VERIFIED | `docs/API.md` includes Java 11 `HttpClient`, curl examples, error envelope, and CLI-only import/index workflow. |
| 4 | Reviewer can follow a minimal demo flow or sample client. | VERIFIED / HUMAN CHECK | `scripts/demo_smoke.py` runs offline and supports opt-in live `/api/search`; `docs/DEMO.md` documents full sample import/index/start/search/latency flow. Live provider run remains manual. |
| 5 | Docs state local-file assumptions, score semantics, formula mapping behavior, privacy-conscious logging, and out-of-scope behavior. | VERIFIED | README/API/DEMO/DEPLOYMENT docs include local Excel/local structured source, score safety semantics, privacy logging guidance, and v1 out-of-scope boundaries. |

**Score:** 5/5 must-haves verified by repository automation; live browser/provider/Docker confirmation remains human UAT.

## Automated Verification

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_documentation_contract.py tests/test_search_api.py tests/test_status_api.py tests/test_smoke_queries.py tests/test_quality_regression_contract.py -q` | `39 passed, 14 warnings` |
| `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/demo_smoke.py --queries tests/fixtures/smoke_queries.json --mode offline --limit 2 --json` | Passed; JSON output includes `mode`, `query_count`, `results`, and `score_semantics` without banned medical labels. |
| `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline --runs 2 --warmups 1` | `thresholds_passed: true`, P50 0.067 ms, P95 0.108 ms, max 0.108 ms. |
| `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts` | All checks passed. |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| DOC-01 | SATISFIED / HUMAN CHECK | OpenAPI route assertions and API docs exist; browser `/docs` should be opened in a running service. |
| DOC-02 | SATISFIED | Java and curl examples are documented in `docs/API.md`. |
| DOC-03 | SATISFIED / HUMAN CHECK | `.env.example`, Dockerfile, Compose, and deployment runbook exist; Docker/provider runtime requires target environment validation. |
| DOC-04 | SATISFIED | Docs cover local-file assumptions, score semantics, formula mapping behavior, privacy-conscious logging, and out-of-scope chat/admin/NER/MySQL sync behavior. |
| DOC-05 | SATISFIED / HUMAN CHECK | Offline demo client passes; live demo requires a running configured service. |

## Human Verification Required

### 1. Browser OpenAPI Review

Start the API and open `/docs`.

**Expected:** Swagger exposes only `/api/search`, `/status`, `/health/live`, and `/health/ready` for HTTP integration.

### 2. Live Demo and Docker Review

Configure provider/reranker settings, import the workbook, rebuild/activate the index, start the API, and run:

```bash
uv run python scripts/demo_smoke.py --mode live --base-url http://127.0.0.1:8000
docker compose up --build
```

**Expected:** Live demo and Docker startup behavior match `docs/DEMO.md` and `docs/DEPLOYMENT.md`.

## Gaps Summary

No repository automation or documentation gaps remain for Phase 5. Status is `human_needed` because browser rendering, Docker daemon behavior, provider credentials, and live model/runtime readiness are environment-specific.

---

_Verified: 2026-06-16T22:20:00+08:00_
_Verifier: Codex (gsd-execute-phase)_
