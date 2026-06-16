---
phase: 05-documentation-and-demo-delivery
plan: 01
subsystem: documentation
tags: [fastapi, openapi, java-integration, safety, pytest]
requires:
  - phase: 03-hybrid-search-and-rerank-api
    provides: "Search, status, health routes and Java-facing response/error contracts"
provides:
  - "Top-level README runbook for the retrieval-only MVP"
  - "API and Java integration guide documenting real HTTP route surface"
  - "OpenAPI/documentation drift tests for routes, schemas, CLI import clarification, and score semantics"
affects: [05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["OpenAPI route assertions", "Documentation contract tests", "CLI import vs HTTP API boundary"]
key-files:
  created:
    - docs/API.md
    - tests/test_documentation_contract.py
  modified:
    - README.md
key-decisions:
  - "Import/rebuild remain CLI-only operator workflows in v1; OpenAPI documents only real HTTP routes."
  - "Docs use retrieval/ranking/reference language and explicitly avoid medical confidence, diagnosis probability, and prescription certainty claims."
requirements-completed: [DOC-01, DOC-02, DOC-04]
duration: 10min
completed: 2026-06-16
---

# Phase 05 Plan 01: API Documentation Summary

**MVP API docs and Java examples now describe the actual search/status/health HTTP surface and CLI-only import workflow**

## Performance

- **Duration:** 10 min
- **Completed:** 2026-06-16
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Replaced the stale README with a reviewer/developer runbook for the retrieval-only service.
- Added `docs/API.md` covering OpenAPI, `/api/search`, `/status`, health routes, error envelope, Java 11 `HttpClient`, curl examples, and score safety semantics.
- Added documentation contract tests that assert current OpenAPI paths, `PatientSearchRequest` fields, README links, and the absence of invented HTTP import/rebuild routes.

## Files Created/Modified

- `README.md` - MVP overview, quick start, API/demo/deployment links, safety and privacy notes.
- `docs/API.md` - HTTP API and Java integration guide.
- `tests/test_documentation_contract.py` - OpenAPI and documentation drift regression tests.

## Decisions Made

- Kept import/rebuild documented as operator CLI commands rather than adding or claiming HTTP endpoints.
- Used score wording as ranking/reference semantics only, not medical confidence or prescription certainty.

## Deviations from Plan

None.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_documentation_contract.py -q` passed as part of the final Phase 5 verification suite.

## User Setup Required

None for documentation contract validation. Live API inspection requires starting the service and opening `/docs`.
