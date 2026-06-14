---
phase: 01-local-data-contract-and-ingestion
verified: 2026-06-14T08:33:22Z
status: passed
score: 17/17 must-haves verified
overrides_applied: 0
---

# Phase 1: Local Data Contract and Ingestion Verification Report

**Phase Goal:** System can convert the real `伤寒论` Excel sample into stable local knowledge entries with preserved source evidence and deterministic IDs.  
**Verified:** 2026-06-14T08:33:22Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Operator can import the real workbook and see total, valid, skipped, warning, failure, indexed, and version counts. | VERIFIED | `import_workbook_to_metadata()` reads the sample Excel and returns `ImportReport`; tests and smoke show `total_rows=1331`, `valid/indexed=1246`, warning/failure fields, and `index_version=local-*`. |
| 2 | Every imported searchable row has a deterministic `entry_id` independent of sparse Excel `编码`. | VERIFIED | `make_entry_id()` hashes stable content parts; mapper stores `编码` only as `source_code`; tests confirm repeated mapping is stable and not equal to source code. |
| 3 | All 22 source columns, raw records, normalized records, and evidence fields remain auditable through local metadata storage. | VERIFIED | `SOURCE_HEADERS` has 22 fields; `raw_records.raw_json` preserves all fields; `KnowledgeEntry` stores raw/normalized records and evidence fields; SQLite/JSONL round-trip tests pass. |
| 4 | Ambiguous or multi-formula `推荐方剂` content preserves raw text and exposes structured mentions or `needs_review`. | VERIFIED | `parse_formula_mentions()` marks ambiguity via `AMBIGUITY_PATTERN`; `formula_mapping_status()` returns `needs_review`; report warnings count ambiguous rows. |
| 5 | `retrieval_text` uses agreed core fields and can be rebuilt without customer MySQL. | VERIFIED | `RETRIEVAL_FIELDS` matches DATA-06; `load_entries_for_rebuild()` reads SQLite only; no MySQL/SQLAlchemy references in source/tests. |
| 6 | Canonical entries expose required contract fields. | VERIFIED | `KnowledgeEntry` includes `entry_id`, `source_code`, `formula_raw`, `formula_mentions`, `formula_mapping_status`, `retrieval_text`, `raw_record`, and `normalized_record`. |
| 7 | Real workbook uses row 3 headers and row 4 first data row. | VERIFIED | `read_excel(..., header=2)` and `source_row = int(index) + 4`; tests assert first data row is source row 4. |
| 8 | Import validation reports valid, skipped, warning, and failed row details. | VERIFIED | `validate_source_row()` emits missing searchable/formula/evidence errors and ambiguity warnings; `build_import_report()` aggregates counts and failed rows. |
| 9 | Operator can inspect/import through local CLI without MySQL or admin console. | VERIFIED | Typer commands `inspect-workbook`, `import-excel`, `rebuild-source`, and `jsonl-export` path exist; dependency scan found no MySQL/admin-console dependency. |
| 10 | Raw and normalized local metadata can rebuild later index versions after re-import. | VERIFIED | Code-review fix implemented `(batch_id, entry_id)` primary key; smoke imported twice and both old/new `index_version` rebuild to 1246 entries. |
| 11 | Import artifacts avoid leaking raw row text to CLI logs while preserving metadata. | VERIFIED | CLI prints report/count JSON only; raw row content is stored in SQLite `raw_records` and optional JSONL. |

**Score:** 17/17 must-haves verified, combining 5 ROADMAP success criteria and 12 PLAN truth must-haves.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `pyproject.toml` | Python 3.12 scaffold and Phase 1 pinned deps | VERIFIED | Contains Pydantic, pandas, openpyxl, Typer, pytest, ruff only for Phase 1 scope. |
| `src/zyfangji_retrieval/domain/models.py` | Canonical Pydantic contracts | VERIFIED | `FormulaMention`, `KnowledgeEntry`, mapping status literal, raw/normalized/evidence fields present. |
| `src/zyfangji_retrieval/domain/ids.py` | Deterministic IDs | VERIFIED | SHA-256 content fingerprint and `shl_` 16-hex ID helper. |
| `src/zyfangji_retrieval/ingestion/retrieval_text.py` | 22 source headers and DATA-06 retrieval text | VERIFIED | Source headers and labeled deterministic retrieval fields present. |
| `src/zyfangji_retrieval/ingestion/formulas.py` | Conservative formula parsing | VERIFIED | Ambiguity pattern, mention extraction, `needs_review` status present. |
| `src/zyfangji_retrieval/ingestion/excel_reader.py` | Workbook reader | VERIFIED | Local `Path` only, `header=2`, strips values, validates exact headers, counts blank rows. |
| `src/zyfangji_retrieval/ingestion/mapper.py` | Row-to-entry mapper | VERIFIED | Preserves 22 raw fields, normalized map, validation, evidence fields, deterministic ID. |
| `src/zyfangji_retrieval/ingestion/reports.py` | Import report models | VERIFIED | Required counts, failed row list, and `metadata_version=local-v1`. |
| `src/zyfangji_retrieval/ingestion/importer.py` | End-to-end local import/rebuild loading | VERIFIED | Reads workbook, validates/maps, saves SQLite batch, loads rebuild entries by optional version. |
| `src/zyfangji_retrieval/persistence/sqlite.py` | Local metadata store | VERIFIED | Four required tables plus versioned `knowledge_entries` snapshots by `(batch_id, entry_id)`. |
| `src/zyfangji_retrieval/persistence/jsonl.py` | UTF-8 audit export/load | VERIFIED | One JSON object per line; Chinese text preserved by tests. |
| `src/zyfangji_retrieval/cli.py` | Local operator CLI | VERIFIED | Persistent import, dry-run, JSONL export, rebuild-source count. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `excel_reader.py` | real workbook | `pandas.read_excel(..., header=2)` | WIRED | Reads `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` correctly in tests. |
| `mapper.py` | domain models/IDs/formula/retrieval modules | constructs `KnowledgeEntry` | WIRED | Uses `make_entry_id`, formula parsing, retrieval text, raw/normalized records. |
| `importer.py` | SQLite metadata store | `SQLiteMetadataStore.save_import()` | WIRED | Persists batches, raw rows, entries, and issues in one transaction. |
| `sqlite.py` | domain models | `KnowledgeEntry.model_validate_json()` | WIRED | Rebuild loading returns typed entries. |
| `cli.py` | importer/report/persistence | Typer commands | WIRED | CLI invokes persistent import and rebuild-source from local metadata. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `excel_reader.py` | `WorkbookRows.rows` | `pandas.read_excel()` on real workbook | Yes, 1331 rows including blanks, 1246 valid entries after mapping | FLOWING |
| `mapper.py` | `KnowledgeEntry` | `WorkbookRow.raw_record` | Yes, all 22 fields mapped to raw/normalized/evidence fields | FLOWING |
| `reports.py` | `ImportReport` counts | workbook rows, entries, row issues | Yes, counts computed from actual import objects | FLOWING |
| `sqlite.py` | rebuild entries | SQLite `knowledge_entries.normalized_json` | Yes, latest and version-specific snapshots load typed entries | FLOWING |
| `cli.py` | JSON output | importer and SQLite metadata | Yes, report/count JSON produced from persisted local data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Contract, ingestion, persistence tests | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q` | `42 passed in 6.55s` | PASS |
| Lint | `UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run ruff check src tests` | `All checks passed!` | PASS |
| GSD artifact checks | `gsd-tools verify artifacts` for all 3 plans | 13/13 artifacts passed | PASS |
| GSD key-link checks | `gsd-tools verify key-links` for all 3 plans | 8/8 links verified | PASS |
| Versioned snapshot smoke | Import sample workbook twice into `/tmp`, then rebuild both versions | first/second/latest rebuild counts all 1246; 2 batches; 2492 entry snapshot rows; same entry ID set | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| DATA-01 | 01-01 | Canonical schema separates IDs, source code/reference, formula fields, mapping status, raw source record. | SATISFIED | `KnowledgeEntry` and `FormulaMention` fields verified. |
| DATA-02 | 01-02 | Preserve all 22 source columns as metadata. | SATISFIED | `SOURCE_HEADERS`, mapper raw record, SQLite raw JSON all preserve 22 fields. |
| DATA-03 | 01-01 | Deterministic `entry_id` without sparse Excel `编码`. | SATISFIED | `ids.py` has no `编码`; mapper stores `source_code` separately. |
| DATA-04 | 01-01 | Multi-formula ambiguity not hidden. | SATISFIED | Ambiguous rows get `needs_review` and warning issues while preserving raw formula text. |
| DATA-05 | 01-01 | Core searchable fields distinct from display-only evidence. | SATISFIED | `RETRIEVAL_FIELDS` excludes pathology/contraindication/effect; evidence still stored. |
| DATA-06 | 01-01 | `retrieval_text` uses main/sub part, symptoms, alias, tongue, pulse, syndrome. | SATISFIED | `RETRIEVAL_FIELDS` exactly covers the agreed field set. |
| ING-01 | 01-02 | Import real workbook and skip title/header rows. | SATISFIED | `header=2`, first data source row 4, tests read real workbook. |
| ING-02 | 01-02 | Report total/valid/skipped/warning/failed/indexed/version counts. | SATISFIED | `ImportReport` fields and real import output verified. |
| ING-03 | 01-02 | Validate required searchable, formula, source/evidence fields. | SATISFIED | `validate_source_row()` covers missing searchable text, formula, evidence, and ambiguity warning. |
| ING-04 | 01-03 | Store raw and normalized records locally for audit. | SATISFIED | SQLite and JSONL persist raw/normalized metadata; tests round-trip. |
| ING-05 | 01-03 | Rebuild indexes from local metadata without customer MySQL. | SATISFIED | `load_entries_for_rebuild()` reads SQLite; dependency scan found no MySQL requirement. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `src/zyfangji_retrieval/ingestion/formulas.py` | 14 | `return []` | Info | Correct empty result for blank formula text, covered by tests. |
| Multiple source/test files | various | initial empty lists/dicts | Info | Local accumulators or test fixtures; not user-visible stubs. |

### Human Verification Required

None. Phase 1 is backend ingestion/persistence code with deterministic local commands; visual or external-service UAT is not required.

### Deferred Items

None for Phase 1 goal. Qdrant/BM25 index construction, hybrid search, API serving, and demo documentation are explicitly later phases.

### Residual Risks

- Formula mention parsing is intentionally conservative and flags ambiguous branch text for review; it does not yet map to a customer formula-code authority.
- SQLite metadata is sufficient for MVP local rebuilds; production backup/retention policy is not covered in Phase 1.
- Source workbook schema is validated exactly against the current 22-column sample; future 200-book schema variation needs a later mapping layer.

### Gaps Summary

No blocking gaps found. Phase 1 achieves the local data contract, validated Excel ingestion, deterministic IDs, local audit persistence, and versioned rebuild source required before Phase 2 index lifecycle planning.

---

_Verified: 2026-06-14T08:33:22Z_  
_Verifier: Claude (gsd-verifier)_
