---
phase: 01-local-data-contract-and-ingestion
plan: 01
subsystem: data-contract
tags: [python, pydantic, pandas, openpyxl, pytest, ruff, ingestion]
requires: []
provides:
  - Python 3.12 src-layout project scaffold with pinned Phase 1 dependencies
  - Canonical Pydantic contracts for knowledge entries and formula mentions
  - Deterministic shl-prefixed SHA-256 entry identifiers
  - Shanghanlun 22-column source header manifest and DATA-06 retrieval_text builder
  - Conservative formula mention parsing with needs_review ambiguity status
affects: [phase-01-ingestion, phase-02-indexing, phase-03-result-contract]
tech-stack:
  added: [pydantic==2.13.4, pandas==3.0.3, openpyxl==3.1.5, typer==0.26.7, pytest==9.1.0, ruff==0.15.17]
  patterns: [src-layout package, Pydantic v2 domain models, pure ingestion helper functions, TDD contract tests]
key-files:
  created:
    - pyproject.toml
    - uv.lock
    - src/zyfangji_retrieval/domain/models.py
    - src/zyfangji_retrieval/domain/ids.py
    - src/zyfangji_retrieval/ingestion/retrieval_text.py
    - src/zyfangji_retrieval/ingestion/formulas.py
    - tests/test_domain_contracts.py
  modified: []
key-decisions:
  - "Use explicit canonical contracts before reading the workbook so later ingestion/indexing code cannot conflate entry_id with sparse source 编码."
  - "Keep formula parsing conservative: extract simple mentions when possible, but mark branch-heavy 推荐方剂 text as needs_review."
patterns-established:
  - "Contract helpers are pure functions with no raw row logging or external side effects."
  - "retrieval_text uses deterministic labeled sections and excludes long display-only evidence fields."
requirements-completed: [DATA-01, DATA-03, DATA-04, DATA-05, DATA-06]
duration: 8min
completed: 2026-06-14
---

# Phase 01 Plan 01: Data Contract Scaffold Summary

**Pydantic knowledge-entry contracts, deterministic `shl_` IDs, DATA-06 retrieval text, and conservative formula ambiguity status**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-14T07:46:37Z
- **Completed:** 2026-06-14T07:54:01Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Created a Python 3.12 `src` layout with pinned Phase 1 dependencies and dev tooling.
- Added canonical `KnowledgeEntry`, `FormulaMention`, `RawSourceRecord`, and `FormulaMappingStatus` contracts.
- Added deterministic `content_fingerprint` and `make_entry_id` helpers that do not read Excel `编码`.
- Added exact 22-column source headers, exact DATA-06 retrieval fields, deterministic `retrieval_text`, and conservative formula ambiguity handling.
- Added contract tests covering IDs, model serialization, retrieval text, and formula status behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Python project scaffold and pinned dependencies** - `161ea57` (`chore`)
2. **Task 2 RED: Define canonical models and deterministic identifiers tests** - `a238ba3` (`test`)
3. **Task 2 GREEN: Define canonical models and deterministic identifiers** - `d78f804` (`feat`)
4. **Task 3 RED: Define retrieval-text and formula ambiguity tests** - `e6061fc` (`test`)
5. **Task 3 GREEN: Define retrieval-text and formula ambiguity contracts** - `9621e65` (`feat`)

## Files Created/Modified

- `pyproject.toml` - Python package metadata, pinned dependencies, pytest config, ruff config, CLI entry point declaration.
- `uv.lock` - Locked dependency graph for the Phase 1 Python environment.
- `src/zyfangji_retrieval/domain/models.py` - Pydantic canonical data contracts.
- `src/zyfangji_retrieval/domain/ids.py` - Deterministic content fingerprint and entry ID helpers.
- `src/zyfangji_retrieval/ingestion/retrieval_text.py` - Source header manifest and retrieval text builder.
- `src/zyfangji_retrieval/ingestion/formulas.py` - Formula mention parser and mapping status helper.
- `tests/test_domain_contracts.py` - Focused contract tests for Phase 1 data behavior.

## Decisions Made

- `entry_id` generation is based only on explicit stable content parts passed by callers, never on source `编码`.
- `FormulaMention.code` is separate from `KnowledgeEntry.formula_raw`, allowing future business formula-code mapping without mutating source text.
- Ambiguous formula text with branch delimiters, numbered branches, alternatives, or cold/hot qualifiers returns `needs_review`.
- Display-only evidence fields such as pathology, contraindications, and efficacy are preserved for later metadata but excluded from `retrieval_text`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used a temp uv environment for verification on the external volume**
- **Found during:** Task 1 verification
- **Issue:** Global `python3` is too old for `tomllib`, and `uv sync` into `.venv` on the KINGSTON volume failed installing `ruff` because macOS `._ruff` sidecar metadata violated wheel RECORD validation.
- **Fix:** Ran verification with `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv`, which provisioned Python 3.12.12 and installed the pinned dependencies cleanly.
- **Files modified:** None
- **Verification:** `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv sync`, pytest, and ruff all passed.
- **Committed in:** N/A, environment-only workaround

---

**Total deviations:** 1 auto-fixed blocking issue.
**Impact on plan:** No product scope change and no dependency pin changes.

## Issues Encountered

- The exact plan command `python3 - <<'PY' ... import tomllib` is blocked by the machine's older global Python. The equivalent check passed under the project-managed Python 3.12 environment.

## Verification

- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv sync` - passed
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py -q` - passed, 16 tests
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` - passed

## Known Stubs

None. Stub scan only found deliberate empty dictionaries/strings in tests for validation and missing-status behavior.

## Threat Flags

None. No new network endpoints, auth paths, file access paths, or persistence schema trust boundaries were introduced beyond the planned local contract helpers.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02 can now build workbook ingestion on top of stable source headers, canonical models, formula status semantics, and deterministic retrieval text.

## Self-Check: PASSED

- Created files exist: `pyproject.toml`, `uv.lock`, domain modules, ingestion modules, and `tests/test_domain_contracts.py`.
- Task commits found: `161ea57`, `a238ba3`, `d78f804`, `e6061fc`, `9621e65`.
- Verification commands passed with the documented uv temp-environment workaround.

---
*Phase: 01-local-data-contract-and-ingestion*
*Completed: 2026-06-14*
