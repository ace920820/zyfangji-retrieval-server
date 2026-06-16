---
status: partial
phase: 04-quality-safety-and-performance-validation
source: [04-VERIFICATION.md]
started: 2026-06-16T13:32:00Z
updated: 2026-06-16T13:32:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Run live latency against configured /api/search

command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python scripts/search_latency.py --queries tests/fixtures/smoke_queries.json --mode live --base-url http://127.0.0.1:8000 --enforce-thresholds
```

expected: warm indexed search reports P50 < 500ms and P95 < 1s, excluding import, index rebuild, and corpus embedding generation.
result: [pending]

### 2. Review smoke query ranking with doctor/customer input

expected: headache, fever/aversion-to-wind, no-sweat/pulse, tongue/pulse, formula, article, and broad/sparse query cases return useful ranked formula candidates with source evidence and contraindication/risk fields visible.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
