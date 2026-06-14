---
phase: 01-local-data-contract-and-ingestion
plan: 02
subsystem: local-excel-ingestion
tags: [python, pandas, openpyxl, pydantic, typer, ingestion, cli]
requires: [01-01]
provides:
  - Shanghanlun workbook reader using Excel row 3 headers and data from row 4
  - Exact 22-column source header validation with fail-closed ValueError behavior
  - Workbook row mapping into canonical KnowledgeEntry records with raw source preservation
  - Row-level validation issues for missing searchable text, formula text, evidence, and formula ambiguity
  - ImportReport JSON counts and local inspect/import dry-run CLI commands
affects: [phase-01-persistence, phase-02-indexing, phase-03-api-contract]
tech-stack:
  added: [hatchling build backend]
  patterns: [TDD ingestion contracts, Path-only local workbook reader, row issue reporting, Typer operator CLI]
key-files:
  created:
    - README.md
    - src/zyfangji_retrieval/cli.py
    - src/zyfangji_retrieval/ingestion/excel_reader.py
    - src/zyfangji_retrieval/ingestion/mapper.py
    - src/zyfangji_retrieval/ingestion/reports.py
    - tests/test_excel_ingestion.py
  modified:
    - .gitignore
    - pyproject.toml
    - uv.lock
key-decisions:
  - "Validate the workbook against the exact SOURCE_HEADERS manifest before any row mapping."
  - "Keep Excel 编码 as source_code only; entry_id is generated from source identity and stable row content."
  - "CLI dry-run output reports counts, source rows, issue codes, and messages, but never raw row text."
  - "Install the src-layout project with a build backend so required python -m CLI verification works without PYTHONPATH."
requirements-completed: [DATA-02, ING-01, ING-02, ING-03]
duration: 25min
completed: 2026-06-14
---

# Phase 01 Plan 02: Excel Ingestion and Import Report Summary

**Local Shanghanlun Excel ingestion with 22-column preservation, canonical row mapping, validation reports, and dry-run CLI output**

## Performance

- **Duration:** 25 min
- **Completed:** 2026-06-14T08:04:33Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Added `read_shanghanlun_workbook()` using `pandas.read_excel(..., header=2, dtype=str, keep_default_na=False)` so the real workbook uses Excel row 3 as headers and Excel row 4 as the first source data row.
- Added exact header validation against the 22 `SOURCE_HEADERS` values and fail-closed `ValueError` behavior for missing or reordered headers.
- Added `WorkbookRow` and `WorkbookRows`, including blank-row counting for import reporting while omitting blank rows from emitted row objects.
- Added `validate_source_row()` and `map_row_to_entry()` to preserve all 22 source columns in `raw_record`, build normalized fields, keep `source_code` separate from `entry_id`, and construct `KnowledgeEntry` records.
- Added `RowIssue`, `ImportReport`, and `build_import_report()` with total, valid, skipped, warning, failed, indexed, index-version, and metadata-version fields.
- Added Typer CLI commands:
  - `inspect-workbook`
  - `import-excel --dry-run/--no-dry-run`

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Read and validate workbook shape tests** - `c62a02d` (`test`)
2. **Task 1 GREEN: Workbook reader implementation** - `aec7644` (`feat`)
3. **Task 2 RED: Row mapper tests** - `9c187ac` (`test`)
4. **Task 2 GREEN: Mapper and row issue model** - `f9b9950` (`feat`)
5. **Task 3 RED: Import report and CLI tests** - `3dec420` (`test`)
6. **Task 3 GREEN: Import report and CLI implementation** - `8209f44` (`feat`)
7. **Verification fix: CLI module executable via uv** - `318a66b` (`fix`)

## Files Created/Modified

- `src/zyfangji_retrieval/ingestion/excel_reader.py` - Workbook dataclasses, exact header validation, source row mapping, and blank-row counting.
- `src/zyfangji_retrieval/ingestion/mapper.py` - Source row validation, normalized-field mapping, deterministic entry ID creation, formula status handling, and `KnowledgeEntry` construction.
- `src/zyfangji_retrieval/ingestion/reports.py` - `RowIssue`, `ImportReport`, and report-count builder.
- `src/zyfangji_retrieval/cli.py` - Local operator CLI for workbook inspection and dry-run imports.
- `tests/test_excel_ingestion.py` - TDD coverage for workbook shape, mapper behavior, report JSON, CLI output, and ambiguity warnings.
- `.gitignore` - Python generated-file ignores.
- `pyproject.toml` and `uv.lock` - Build backend metadata so module-style CLI execution works under `uv`.
- `README.md` - Minimal package README referenced by project metadata.

## Decisions Made

- `total_rows` counts emitted workbook rows plus blank rows skipped by the reader; `skipped_rows` counts blank rows plus rows with validation errors.
- `failed_rows` intentionally contains row numbers and issue metadata only, not full source records or clinical-like raw row text.
- Persistent import remains blocked with `typer.BadParameter("persistent import is implemented in Plan 03")`.
- Formula ambiguity is a warning (`formula_needs_review`) and does not prevent a row from becoming a valid canonical entry.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ignored generated Python/tool cache files**
- **Found during:** Task 1 RED verification
- **Issue:** Running pytest created `__pycache__`, `.pytest_cache`, and `.ruff_cache` artifacts in the worktree.
- **Fix:** Added standard generated-file patterns to `.gitignore` and removed generated cache directories from the worktree.
- **Files modified:** `.gitignore`
- **Commit:** `c62a02d`

**2. [Rule 3 - Blocking] Added `RowIssue` before the full report task**
- **Found during:** Task 2 implementation
- **Issue:** `validate_source_row()` is required to return `list[RowIssue]`, but `reports.py` was otherwise scheduled for Task 3.
- **Fix:** Added the minimal `RowIssue` Pydantic model in Task 2, then extended the same module with `ImportReport` in Task 3.
- **Files modified:** `src/zyfangji_retrieval/ingestion/reports.py`
- **Commit:** `f9b9950`

**3. [Rule 2 - Critical Functionality] Counted blank workbook rows in reports**
- **Found during:** Task 3 implementation
- **Issue:** Task 1 correctly skipped blank rows from emitted `WorkbookRow` objects, but Task 3 also needed skipped blank rows represented in import counts.
- **Fix:** Added `blank_rows` to `WorkbookRows` and included it in `total_rows` and `skipped_rows`.
- **Files modified:** `src/zyfangji_retrieval/ingestion/excel_reader.py`, `src/zyfangji_retrieval/ingestion/reports.py`
- **Commit:** `8209f44`

**4. [Rule 3 - Blocking] Made the src-layout package installable for required CLI verification**
- **Found during:** Final verification
- **Issue:** `uv run python -m zyfangji_retrieval.cli ...` failed because the project had no build backend and was not installed into the uv environment; enabling packaging exposed the referenced but missing `README.md`.
- **Fix:** Added a Hatchling build backend, refreshed `uv.lock`, and added the missing package README.
- **Files modified:** `pyproject.toml`, `uv.lock`, `README.md`
- **Commit:** `318a66b`

---

**Total deviations:** 4 auto-fixed issues.
**Impact on plan:** No scope expansion beyond local ingestion/reporting; fixes made planned verification and reporting semantics work end to end.

## Verification

- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv sync` - passed
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_excel_ingestion.py -q` - passed, 12 tests
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python -m zyfangji_retrieval.cli inspect-workbook "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx"` - passed
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run python -m zyfangji_retrieval.cli import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --dry-run` - passed
- `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` - passed

## Import Dry-Run Result

- `total_rows`: 1331
- `valid_rows`: 1246
- `skipped_rows`: 85
- `warning_count`: 221
- `indexed_count`: 1246
- `index_version`: `dry-run`
- `metadata_version`: `local-v1`

## Known Stubs

None. Stub scan findings were typed empty lists in implementation/tests and optional `None` fields in domain contracts, not UI/data-source stubs.

## Threat Flags

None. The new local workbook parser, row mapper, and CLI output paths are the planned trust boundaries in the plan threat model; no unplanned network endpoint, auth path, persistence schema, or remote file fetch behavior was introduced.

## User Setup Required

None. Verification uses the existing `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv` workaround from Plan 01 for the external drive.

## Next Phase Readiness

Plan 03 can persist the validated `KnowledgeEntry` records and `ImportReport` results locally, using the dry-run counts and row issue metadata produced here as the import contract.

## Self-Check: PASSED

- Created files exist: `README.md`, `src/zyfangji_retrieval/cli.py`, `src/zyfangji_retrieval/ingestion/excel_reader.py`, `src/zyfangji_retrieval/ingestion/mapper.py`, `src/zyfangji_retrieval/ingestion/reports.py`, `tests/test_excel_ingestion.py`, and this summary.
- Task and fix commits found: `c62a02d`, `aec7644`, `9c187ac`, `f9b9950`, `3dec420`, `8209f44`, `318a66b`.
- Required verification commands passed with `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv`.

---
*Phase: 01-local-data-contract-and-ingestion*
*Completed: 2026-06-14*
