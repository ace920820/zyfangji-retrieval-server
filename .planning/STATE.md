# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-14)

**Core value:** 医生输入患者症状后，系统必须能稳定返回有典籍依据、排序合理、可回连业务方剂库的推荐方剂列表。
**Current focus:** Phase 1: Data Contract and Canonical Ingestion

## Current Position

Phase: 1 of 5 (Data Contract and Canonical Ingestion)
Plan: 0 of 3 in current phase
Status: Ready to plan
Last activity: 2026-06-14 — Roadmap created from 45 v1 requirements with full phase traceability.

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Data Contract and Canonical Ingestion | 0/3 | - | - |
| 2. Index Lifecycle and Admin Operations | 0/3 | - | - |
| 3. Search API and Evidence Results | 0/3 | - | - |
| 4. Retrieval Quality and Safety Validation | 0/2 | - | - |
| 5. Documentation and Demo Delivery | 0/3 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: v1 remains retrieval-only; chat, generative diagnosis, private LLM deployment, and prescription composition joins stay out of scope.
- [Roadmap]: Phase 1 starts with data contract and canonical ingestion because stable IDs and evidence preservation are prerequisites for indexing and Java integration.
- [Roadmap]: Java backend owns patient workflow and prescription composition joins; retrieval service returns formula identifiers, mapping status, and evidence.
- [Roadmap]: Coarse granularity uses five phases to respect dependencies while keeping the two-to-three-week demo practical.

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2]: Final embedding provider, model dimensions, quota, latency, and region/account availability still need confirmation.
- [Phase 3]: Business formulary mapping table may be unavailable; v1 must allow `formula_code: null` with explicit mapping status.
- [Phase 4]: Representative doctor queries are needed to make regression tests meaningful beyond generic smoke queries.
- [Phase 5]: Demo admin protection, provider-key handling, and privacy/logging expectations need confirmation before external exposure.

## Session Continuity

Last session: 2026-06-14
Stopped at: Roadmap, state, and requirement traceability initialized.
Resume file: None
