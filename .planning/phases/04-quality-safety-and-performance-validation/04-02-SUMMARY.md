---
phase: 04-quality-safety-and-performance-validation
plan: 02
subsystem: quality
tags: [pytest, smoke-tests, latency, search-api, safety]
requires:
  - phase: 03-hybrid-search-and-rerank-api
    provides: "SearchService contract, /api/search response schema, evidence projection, and query warning semantics"
provides:
  - "Structured smoke query fixture covering symptom, tongue, pulse, formula, article, and broad-query paths"
  - "Offline deterministic smoke regression tests for safe ranked search responses"
  - "JSON latency harness with offline default and opt-in live /api/search mode"
affects: [04-quality-safety-and-performance-validation, 05-documentation-and-demo-delivery]
tech-stack:
  added: []
  patterns: ["Fixture-driven smoke regression", "Offline deterministic latency measurement", "Opt-in live HTTP validation"]
key-files:
  created:
    - tests/fixtures/smoke_queries.json
    - tests/test_smoke_queries.py
    - scripts/search_latency.py
  modified: []
key-decisions:
  - "Smoke expectations assert stable fields, warning codes, and formula anchors rather than exact scores or exact full ranking."
  - "Default latency measurement runs in-process against deterministic fakes so it does not require Qdrant, BGE-M3, reranker, network, or a running server."
  - "Live latency mode is explicit via --mode live --base-url and reports only request timing, not import, index rebuild, or corpus embedding generation time."
requirements-completed: [QUAL-02, QUAL-03, QUAL-04, QUAL-05]
duration: 16min
completed: 2026-06-16
---

# Phase 04 Plan 02: Smoke Query and Latency Validation Summary

**Fixture-driven TCM smoke queries plus offline/live latency reporting for the indexed search API**

## Performance

- **Duration:** 16 min
- **Completed:** 2026-06-16T13:27:30Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `tests/fixtures/smoke_queries.json` with seven smoke cases covering headache, fever/aversion-to-wind, no sweat with floating-tight pulse, tongue/pulse combination, formula lookup, article reference, and broad sparse query behavior.
- Added `tests/test_smoke_queries.py`, which validates every fixture request through `PatientSearchRequest`, executes deterministic offline search, asserts evidence/contraindication visibility, and recursively bans generated diagnosis/advice/prescribing/confidence fields.
- Added `scripts/search_latency.py`, which prints compact JSON with P50/P95/max timing, thresholds, sample counts, and dataset/index metadata.
- Kept live latency checks opt-in through `--mode live --base-url`, with offline mode as the default for CI and local validation.

## Task Commits

1. **Tasks 1-3: Add smoke fixture, offline smoke tests, and latency harness** - `a628f57` (`test`)

## Files Created/Modified

- `tests/fixtures/smoke_queries.json` - Structured smoke/regression query definitions and expectations.
- `tests/test_smoke_queries.py` - Offline deterministic smoke tests with safety and evidence assertions.
- `scripts/search_latency.py` - JSON-emitting offline/live latency harness.

## Deviations from Plan

None in behavior. The GSD commit wrapper did not stage newly created files, so the implementation commit was made with precise `git add`/`git commit` for the three planned files only.

## Known Stubs

The offline smoke and latency paths use deterministic in-memory stores/retrievers/reranker doubles. They prove response contracts, safety boundaries, warning semantics, and latency harness behavior; they do not prove live Qdrant/BGE-M3/reranker quality or provider latency.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: safety_boundary | `tests/test_smoke_queries.py` | Recursively rejects generated diagnosis/advice/prescribing/confidence keys while requiring score semantics. |
| threat_flag: live_boundary | `scripts/search_latency.py` | Keeps networked `/api/search` timing opt-in; default mode sends no patient query text over the network. |
| threat_flag: latency_interpretation | `scripts/search_latency.py` | Reports mode, sample count, thresholds, and metadata so timing is not confused with medical quality or import/index-build time. |

## Verification

- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python -m json.tool tests/fixtures/smoke_queries.json >/tmp/zyfangji-smoke-queries.json` -> passed.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_smoke_queries.py -q` -> 8 passed, 1 warning.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode offline --runs 2 --warmups 1` -> thresholds passed; P50 0.075 ms, P95 0.128 ms in the sample run.
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check scripts/search_latency.py tests/test_smoke_queries.py` -> All checks passed.

## User Setup Required

None for automated offline validation. Live `/api/search` latency still requires a running service and populated live index.

## Next Phase Readiness

Phase 5 can use the smoke fixture and latency command in demo documentation. Phase 4 final verification should still record live/manual validation needs for real Qdrant, BGE-M3, reranker, and domain ranking review.

## Self-Check: PASSED

- Found summary and key implementation files.
- Found task commit `a628f57` in git history.
