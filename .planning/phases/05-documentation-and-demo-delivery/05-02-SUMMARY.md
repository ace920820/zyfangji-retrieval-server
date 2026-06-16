---
phase: 05-documentation-and-demo-delivery
plan: 02
subsystem: documentation
tags: [demo, smoke-tests, search-api, safety, pytest]
requires:
  - phase: 04-quality-safety-and-performance-validation
    provides: "Smoke query fixture and offline/live latency harness"
provides:
  - "Offline/live reviewer smoke demo client"
  - "Reviewer demo guide connecting import, index rebuild, API startup, smoke search, latency checks, and safe result reading"
  - "Documentation tests proving demo output avoids unsafe medical labels"
affects: [05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["Offline default demo mode", "Explicit opt-in live /api/search mode", "Evidence-focused demo output"]
key-files:
  created:
    - scripts/demo_smoke.py
    - docs/DEMO.md
  modified:
    - README.md
    - tests/test_documentation_contract.py
key-decisions:
  - "Demo smoke defaults to offline deterministic output so reviewers can validate contracts without Qdrant, provider credentials, network, or a running server."
  - "Live demo mode requires explicit --mode live --base-url before sending query payloads over HTTP."
requirements-completed: [DOC-04, DOC-05]
duration: 12min
completed: 2026-06-16
---

# Phase 05 Plan 02: Reviewer Demo Summary

**Offline/live demo client and reviewer guide provide a safe, repeatable smoke-search flow for Phase 5 handoff**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-06-16
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `scripts/demo_smoke.py` with fixture loading, `PatientSearchRequest` validation, offline deterministic mode, opt-in live `/api/search` mode, text output, and JSON summary output.
- Added `docs/DEMO.md` with offline smoke, live API, sample import, index rebuild, API startup, search, latency, manual review, and troubleshooting steps.
- Extended documentation tests to run the offline JSON demo and assert banned labels such as `diagnosis`, `medical_advice`, and `autonomous_prescription` are absent.

## Files Created/Modified

- `scripts/demo_smoke.py` - Reviewer-facing offline/live smoke client.
- `docs/DEMO.md` - Demo guide and safe interpretation checklist.
- `README.md` - Demo guide and sample-client links.
- `tests/test_documentation_contract.py` - Demo contract tests.

## Decisions Made

- Kept networked demo behavior explicit and opt-in.
- Presented formula names, source articles, warning codes, pipeline status, and score semantics without clinical-decision labels.

## Deviations from Plan

None.

## Verification

- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/demo_smoke.py --queries tests/fixtures/smoke_queries.json --mode offline --limit 2 --json` passed.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_documentation_contract.py tests/test_smoke_queries.py -q` covered the demo path through the final suite.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check scripts/demo_smoke.py tests/test_documentation_contract.py` passed through the final ruff run.

## User Setup Required

None for offline demo mode. Live mode requires a running API service with an active index.
