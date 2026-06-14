---
phase: 01
slug: local-data-contract-and-ingestion
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-15
updated: 2026-06-15
---

# Phase 01 - Validation Strategy

> Reconstructed Nyquist validation contract from completed Phase 1 plans, summaries, tests, and verification artifacts.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.0 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q` |
| **Full suite command** | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q`
- **After every plan wave:** Run `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | T-01-01 / local contract | `KnowledgeEntry` separates internal IDs, source code, formula text, formula mentions, mapping status, and raw records. | unit | `pytest tests/test_domain_contracts.py -q` | yes | green |
| 01-01-02 | 01 | 1 | DATA-03 | T-01-01 / local contract | `entry_id` is deterministic and does not depend on sparse Excel `编码`. | unit | `pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py -q` | yes | green |
| 01-01-03 | 01 | 1 | DATA-04 | T-01-01 / local contract | Ambiguous `推荐方剂` preserves raw text and marks `needs_review`. | unit | `pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py -q` | yes | green |
| 01-01-04 | 01 | 1 | DATA-05 | T-01-01 / local contract | Searchable retrieval text excludes display-only evidence fields. | unit | `pytest tests/test_domain_contracts.py -q` | yes | green |
| 01-01-05 | 01 | 1 | DATA-06 | T-01-01 / local contract | `retrieval_text` uses deterministic labeled sections for core searchable fields. | unit | `pytest tests/test_domain_contracts.py -q` | yes | green |
| 01-02-01 | 02 | 2 | DATA-02 | T-01-02 / local file parse | All 22 workbook columns are preserved in `raw_record`. | unit | `pytest tests/test_excel_ingestion.py tests/test_local_persistence.py -q` | yes | green |
| 01-02-02 | 02 | 2 | ING-01 | T-01-02 / local file parse | Real workbook uses Excel row 3 as headers and row 4 as first data row. | integration | `pytest tests/test_excel_ingestion.py -q` | yes | green |
| 01-02-03 | 02 | 2 | ING-02 | T-01-02 / operator output | Import reports expose total, valid, skipped, warning, failed, indexed, and version fields. | unit/integration | `pytest tests/test_excel_ingestion.py tests/test_local_persistence.py -q` | yes | green |
| 01-02-04 | 02 | 2 | ING-03 | T-01-02 / validation | Missing searchable text or formula text is skipped with row issue codes. | unit | `pytest tests/test_excel_ingestion.py -q` | yes | green |
| 01-03-01 | 03 | 3 | ING-04 | T-01-03 / local persistence | Raw source records and normalized records are persisted locally and queryable by source row. | integration | `pytest tests/test_local_persistence.py -q` | yes | green |
| 01-03-02 | 03 | 3 | ING-05 | T-01-03 / rebuild source | Rebuild loading reads persisted metadata without customer MySQL or workbook reparsing. | integration | `pytest tests/test_local_persistence.py -q` | yes | green |

*Status: pending / green / red / flaky*

---

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DATA-01 | COVERED | `tests/test_domain_contracts.py::test_knowledge_entry_separates_source_code_from_entry_id_and_records` |
| DATA-02 | COVERED | `tests/test_excel_ingestion.py::test_valid_workbook_row_maps_to_knowledge_entry_with_all_raw_columns`; `tests/test_local_persistence.py::test_raw_records_are_queryable_by_source_row_and_preserve_all_source_fields` |
| DATA-03 | COVERED | `tests/test_domain_contracts.py::test_make_entry_id_is_deterministic_with_shl_prefix`; `tests/test_excel_ingestion.py::test_entry_id_is_stable_and_not_source_code` |
| DATA-04 | COVERED | `tests/test_domain_contracts.py::test_branchy_formula_text_returns_needs_review`; `tests/test_excel_ingestion.py::test_formula_ambiguity_warning_is_counted_in_report` |
| DATA-05 | COVERED | `tests/test_domain_contracts.py::test_build_retrieval_text_excludes_display_only_evidence_fields` |
| DATA-06 | COVERED | `tests/test_domain_contracts.py::test_build_retrieval_text_emits_non_empty_sections_in_contract_order` |
| ING-01 | COVERED | `tests/test_excel_ingestion.py::test_read_real_workbook_reports_exact_source_headers`; `tests/test_excel_ingestion.py::test_real_workbook_uses_excel_row_3_header_and_row_4_first_data` |
| ING-02 | COVERED | `tests/test_excel_ingestion.py::test_import_report_json_contains_required_counts`; `tests/test_local_persistence.py::test_import_workbook_to_metadata_persists_real_workbook_report` |
| ING-03 | COVERED | `tests/test_excel_ingestion.py::test_missing_searchable_text_skips_row_with_issue_code`; `tests/test_excel_ingestion.py::test_missing_formula_raw_skips_row_with_issue_code` |
| ING-04 | COVERED | `tests/test_local_persistence.py::test_sqlite_metadata_store_creates_required_tables`; `tests/test_local_persistence.py::test_raw_records_are_queryable_by_source_row_and_preserve_all_source_fields`; `tests/test_local_persistence.py::test_jsonl_load_round_trips_knowledge_entries` |
| ING-05 | COVERED | `tests/test_local_persistence.py::test_load_entries_for_rebuild_returns_persisted_entry_count`; `tests/test_local_persistence.py::test_local_persistence_import_does_not_require_customer_mysql`; `tests/test_local_persistence.py::test_rebuild_source_cli_prints_local_metadata_count_without_workbook_parse` |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-06-15

| Metric | Count |
|--------|-------|
| Requirements audited | 11 |
| Gaps found | 0 |
| Resolved by generated tests | 0 |
| Already covered | 11 |
| Escalated | 0 |

Verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_domain_contracts.py tests/test_excel_ingestion.py tests/test_local_persistence.py -q
```

Result: `42 passed in 7.38s`

---

## Validation Sign-Off

- [x] All tasks have automated verification
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-15
