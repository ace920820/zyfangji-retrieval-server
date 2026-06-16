---
phase: 05
slug: documentation-and-demo-delivery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-16
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for documentation, Java integration examples, demo flow, and deployment/runbook packaging.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.0 |
| **Config file** | `pyproject.toml` |
| **Focused docs command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_documentation_contract.py -q` |
| **Demo command** | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/demo_smoke.py --queries tests/fixtures/smoke_queries.json --mode offline` |
| **Lint command** | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests scripts` |
| **Estimated runtime** | ~5 seconds focused docs, ~15 seconds with existing API/status tests |

---

## Sampling Rate

- **After every task commit:** Run the focused docs command if `tests/test_documentation_contract.py` exists.
- **After demo script changes:** Run the demo command plus focused docs command.
- **After Docker/runbook changes:** Run grep-based acceptance checks and `ruff check src tests scripts`.
- **Before `/gsd-verify-work`:** Run focused docs command, demo command, and relevant existing API/status tests.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DOC-01 | T-05-01 / contract drift | OpenAPI docs and README list only real HTTP routes and do not claim a nonexistent HTTP import endpoint. | docs/API contract | `pytest tests/test_documentation_contract.py -q` | no - Wave 0 | pending |
| 05-01-02 | 01 | 1 | DOC-02 | T-05-02 / Java integration drift | Java/curl examples use current request/response fields and document import as CLI/operator workflow. | docs/example contract | `pytest tests/test_documentation_contract.py -q` | no - Wave 0 | pending |
| 05-02-01 | 02 | 1 | DOC-05 | T-05-03 / unsafe demo output | Demo client reads smoke fixtures, validates request payloads, and prints evidence-focused output without diagnosis/advice/prescribing claims. | script/demo smoke | `python scripts/demo_smoke.py --queries tests/fixtures/smoke_queries.json --mode offline` | no - Wave 0 | pending |
| 05-02-02 | 02 | 1 | DOC-04 / DOC-05 | T-05-04 / score misuse | Demo guide states score semantics, evidence/risk interpretation, and live-provider limitations. | docs safety | `pytest tests/test_documentation_contract.py -q` | no - Wave 0 | pending |
| 05-03-01 | 03 | 1 | DOC-03 | T-05-05 / misconfiguration | `.env.example` and runbook document all `ZYFANGJI_` settings and provider/reranker startup modes. | docs/config contract | `pytest tests/test_documentation_contract.py -q` | no - Wave 0 | pending |
| 05-03-02 | 03 | 1 | DOC-03 / DOC-04 | T-05-06 / deployment privacy scope | Docker/Compose/runbook document Qdrant/API runtime, privacy-conscious logging, local-file assumptions, and out-of-scope admin/chat/NER/MySQL sync. | docs/deployment contract | `pytest tests/test_documentation_contract.py -q` | no - Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_documentation_contract.py` - docs/OpenAPI/config/demo contract tests for DOC-01 through DOC-05.
- [ ] `README.md` - top-level MVP runbook and links to detailed docs.
- [ ] `docs/API.md` - HTTP API, OpenAPI, Java/curl examples, CLI import clarification.
- [ ] `docs/DEMO.md` - reviewer demo flow and safe output interpretation.
- [ ] `scripts/demo_smoke.py` - offline/live sample client for smoke fixture search output.
- [ ] `.env.example` - all supported `ZYFANGJI_` settings.
- [ ] `Dockerfile` and `docker-compose.yml` - API + Qdrant packaging or explicitly documented provider boundaries.
- [ ] `docs/DEPLOYMENT.md` - setup, provider/reranker config, Docker Compose, privacy, out-of-scope checklist.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser review of Swagger UI | DOC-01 | Repository tests can verify OpenAPI paths but not browser readability. | Start API, open `http://127.0.0.1:8000/docs`, confirm search/status/health docs render. |
| Clean checkout demo flow | DOC-03 / DOC-05 | Requires local shell, sample workbook availability, optional provider/Qdrant runtime. | Follow README from install through import/rebuild/start/status/search and record blockers. |
| Live provider latency/search demo | DOC-05 | Requires configured BGE-M3 endpoint/reranker/Qdrant runtime. | Run `scripts/search_latency.py --mode live --base-url http://127.0.0.1:8000 --enforce-thresholds` when environment exists. |

---

## Validation Sign-Off

- [ ] All DOC requirements map to at least one automated or manual verification.
- [ ] Documentation tests prevent claiming nonexistent HTTP import endpoints.
- [ ] Java examples use current API schemas.
- [ ] Demo client avoids diagnosis/advice/prescribing/confidence language.
- [ ] `.env.example` covers every `AppSettings` field.
- [ ] Docker/runbook docs state provider/reranker and privacy boundaries.
- [ ] `nyquist_compliant: true` set after execution validates all requirements.

**Approval:** pending
