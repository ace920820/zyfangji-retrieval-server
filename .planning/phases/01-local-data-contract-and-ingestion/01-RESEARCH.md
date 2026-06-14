# Phase 1: Local Data Contract and Ingestion - Research

**Researched:** 2026-06-14  
**Domain:** Excel-to-canonical-record ingestion for a physician-facing TCM retrieval service  
**Confidence:** HIGH for data shape, contract needs, and ingestion architecture; MEDIUM for final persistence layout

## User Constraints

No `01-CONTEXT.md` exists for this phase, so there are no additional locked discuss-phase decisions to copy. [VERIFIED: `node ... gsd-tools.cjs init phase-op 1`]

Project-level constraints still apply: MVP reads local Excel/local structured files, not customer MySQL; Phase 1 must preserve all source fields, generate deterministic IDs independent of sparse `编码`, preserve raw and normalized records, handle multi-formula ambiguity, and generate `retrieval_text` from the agreed core fields. [VERIFIED: `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `AGENTS.md`]

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Define canonical knowledge-entry schema separating `entry_id`, source `编码`, source reference, formula name/code/raw text, mapping status, and raw record. | Use Pydantic domain schemas plus SQLite/JSONL persistence boundaries. [VERIFIED: `.planning/REQUIREMENTS.md`] |
| DATA-02 | Preserve all 22 source columns as retrievable/displayable metadata. | Workbook header row has exactly 22 non-empty headers. [VERIFIED: direct `.xlsx` XML inspection] |
| DATA-03 | Generate deterministic stable `entry_id` without relying on sparse Excel `编码`. | `编码` is non-empty in only 32 of 1,322 non-empty data rows after the header. [VERIFIED: direct `.xlsx` XML inspection] |
| DATA-04 | Represent multi-formula or multi-syndrome rows without hiding ambiguity. | `推荐方剂` is non-empty in 1,246 rows and rough delimiter/branch scan flagged 366 ambiguous-looking formula cells. [VERIFIED: direct `.xlsx` XML inspection] |
| DATA-05 | Distinguish searchable core fields from display-only evidence fields. | `retrieval_text` field list is already constrained to symptom/location/tongue/pulse/syndrome fields. [VERIFIED: `.planning/REQUIREMENTS.md`, `需求文档.md`] |
| DATA-06 | Define `retrieval_text` using main part, sub part, main symptom, complex symptom, detail symptom, alias, tongue, pulse, and syndrome fields. | Use labeled sections in deterministic field order. [VERIFIED: `需求文档.md`] |
| ING-01 | Import the real sample workbook and skip title/header rows correctly. | Sheet has title row 1, grouped heading row 2, actual header row 3, and data starts at row 4. [VERIFIED: direct `.xlsx` XML inspection] |
| ING-02 | Report total, valid, skipped, warning, failed details, indexed count, and index version. | Phase success criteria require these counts. [VERIFIED: `.planning/ROADMAP.md`] |
| ING-03 | Validate required fields for searchable entries. | Core valid rows should require at least symptom text, formula raw text, source reference/source metadata, and evidence fields. [VERIFIED: `.planning/REQUIREMENTS.md`] |
| ING-04 | Store raw and normalized records locally. | MVP explicitly allows SQLite or JSONL metadata storage. [VERIFIED: `需求文档.md`] |
| ING-05 | Rebuild indexes from local metadata without customer MySQL. | Customer MySQL sync is out of scope for v1. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`] |

</phase_requirements>

## Project Constraints (from AGENTS.md)

- Work through GSD planning/execution workflows before repo edits. [VERIFIED: `AGENTS.md`]
- MVP is retrieval-only, not chat, LLM generation, admin console, or customer MySQL sync. [VERIFIED: `AGENTS.md`]
- Preserve evidence fields including contraindications and western-medicine priority advice because the service is used in a medical context. [VERIFIED: `AGENTS.md`]
- Return scores only as ranking/display signals, not medical confidence. [VERIFIED: `AGENTS.md`]
- Java backend integration requires stable HTTP/API contracts later, but Phase 1 should not fetch business formulary composition. [VERIFIED: `AGENTS.md`, `.planning/PROJECT.md`]
- No `CLAUDE.md` exists and no project-local `.claude/skills` or `.agents/skills` were found. [VERIFIED: filesystem checks]

## Summary

Phase 1 should be planned as a greenfield ingestion/data-contract slice: create Python project scaffolding, define canonical Pydantic schemas, parse the real workbook from row 3 headers onward, validate rows into normalized `KnowledgeEntry` records, persist raw plus normalized metadata locally, and produce deterministic import reports. [VERIFIED: repo file scan, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`]

The central risk is not Excel parsing; it is losing auditability or creating unstable identifiers. [VERIFIED: direct `.xlsx` XML inspection, `.planning/research/SUMMARY.md`] The workbook has sparse `编码`, a non-trivial set of blank/non-searchable rows, and many formula cells that encode clinical branches or multiple formulas in one text cell. [VERIFIED: direct `.xlsx` XML inspection]

**Primary recommendation:** use `pandas` + `openpyxl` for workbook ingestion, Pydantic v2 for canonical schemas, and SQLite as the primary local metadata store with optional JSONL export for audit/debug snapshots. [VERIFIED: PyPI JSON API, `需求文档.md`]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.x target | Service/runtime language | Project stack already recommends Python 3.12 for ML/search package compatibility; local host currently has Python 3.9.6, so the plan must add environment setup. [VERIFIED: `.planning/research/STACK.md`, `python3 --version`] |
| pandas | 3.0.3, uploaded 2026-05-11 | Read and normalize tabular Excel data | Best fit for stable column mapping, empty-cell handling, and future CSV/table inputs. [VERIFIED: PyPI JSON API] |
| openpyxl | 3.1.5, uploaded 2024-06-28 | `.xlsx` engine for pandas | Required practical engine for reading Excel `.xlsx` files through pandas. [VERIFIED: PyPI JSON API] |
| pydantic | 2.13.4, uploaded 2026-05-06 | Canonical data schemas and validation | Project stack uses Pydantic v2 with FastAPI; Phase 1 needs strict, serializable domain contracts before API work. [VERIFIED: PyPI JSON API, `.planning/research/STACK.md`] |
| SQLite | 3.51.0 local CLI | Local metadata persistence | MVP requirements allow SQLite/JSONL; SQLite gives queryable import batches, raw records, normalized records, and validation reports without customer MySQL. [VERIFIED: `需求文档.md`, `sqlite3 --version`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.0, uploaded 2026-06-13 | Unit and contract tests | Use for Excel header detection, row validation, stable ID generation, formula parsing status, and retrieval-text construction. [VERIFIED: PyPI JSON API, `.planning/REQUIREMENTS.md`] |
| ruff | 0.15.17, uploaded 2026-06-11 | Formatting/linting | Use as the single formatter/linter for the greenfield Python scaffold. [VERIFIED: PyPI JSON API, `.planning/research/STACK.md`] |
| uv | 0.10.4 local | Python environment/dependency manager | Use for reproducible setup, but plan should not depend on newer `uv pip index` commands because this local `uv` lacks that subcommand. [VERIFIED: `uv --version`, failed `uv pip index versions ...`] |
| Typer | 0.26.7 from project stack | Import CLI | Add when implementing operator commands like `import-excel` and `inspect-workbook`; Phase 1 can expose CLI before HTTP import endpoints. [VERIFIED: `.planning/research/STACK.md`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite primary metadata | JSONL only | JSONL is easy to audit, but SQLite is better for import batches, unique constraints, row lookup by `entry_id`, and status/report queries. [ASSUMED] |
| pandas/openpyxl | Manual `.xlsx` ZIP/XML parsing | XML parsing worked for research inspection, but application code should use a maintained parser to avoid date/string/shared-string/style edge cases. [VERIFIED: direct `.xlsx` XML inspection] |
| Pydantic schemas | Raw dicts/dataclasses only | Raw dicts make schema drift and response-contract reuse harder; Pydantic gives typed validation and JSON serialization for later FastAPI schemas. [ASSUMED] |

**Installation:**
```bash
uv add pandas==3.0.3 openpyxl==3.1.5 pydantic==2.13.4 typer
uv add --dev pytest==9.1.0 ruff==0.15.17
```

**Version verification:** PyPI JSON API verified current package versions for `pandas`, `openpyxl`, `pydantic`, `pytest`, and `ruff` on 2026-06-14. [VERIFIED: PyPI JSON API]

## Architecture Patterns

### Recommended Project Structure

```text
src/
├── zyfangji_retrieval/
│   ├── domain/
│   │   ├── models.py          # Pydantic KnowledgeEntry, RawSourceRecord, FormulaMention
│   │   └── ids.py             # deterministic entry_id generation
│   ├── ingestion/
│   │   ├── excel_reader.py    # workbook/header/row extraction
│   │   ├── mapper.py          # 22-column source -> canonical fields
│   │   ├── formulas.py        # formula mention parsing/status
│   │   └── retrieval_text.py  # deterministic labeled text builder
│   ├── persistence/
│   │   ├── sqlite.py          # import batches, raw records, normalized records
│   │   └── jsonl.py           # optional export/import snapshots
│   └── cli.py                 # import-excel, inspect-workbook
tests/
├── fixtures/
│   └── sample_rows.py
└── test_ingestion_*.py
```

This structure keeps workbook-specific parsing out of domain models and keeps local persistence independent of future Qdrant/BM25 indexing. [ASSUMED]

### Pattern 1: Source Adapter plus Canonical Model

**What:** Treat the `伤寒论` workbook as a source adapter that emits canonical `KnowledgeEntry` records while preserving the full original row in `raw_record`. [VERIFIED: `.planning/REQUIREMENTS.md`]

**When to use:** Use this for Phase 1 because future 200-book expansion may have different field structures and should not leak source-specific headers into search APIs. [VERIFIED: `.planning/PROJECT.md`, `.planning/research/SUMMARY.md`]

**Example:**
```python
from pydantic import BaseModel, Field

class FormulaMention(BaseModel):
    name: str
    code: str | None = None
    branch_label: str | None = None

class KnowledgeEntry(BaseModel):
    entry_id: str
    source_book: str = "伤寒论"
    source_sheet: str
    source_row: int
    source_code: str | None = None
    formula_raw: str
    formula_mentions: list[FormulaMention] = Field(default_factory=list)
    formula_mapping_status: str
    retrieval_text: str
    raw_record: dict[str, str]
    normalized_record: dict[str, str]
```

Source: Pydantic model pattern aligned with project stack and requirements. [VERIFIED: `.planning/research/STACK.md`, `.planning/REQUIREMENTS.md`]

### Pattern 2: Deterministic ID from Stable Source Content

**What:** Generate `entry_id` from source identity plus normalized stable row content, not from `编码` alone. [VERIFIED: `.planning/REQUIREMENTS.md`]

**Recommended input:** `source_book`, `source_sheet`, `source_row`, source reference/article field, main symptom, syndrome, and formula raw text. [ASSUMED]

**Why row number can be included:** Phase 1 needs deterministic IDs for the imported workbook; if future source files reorder rows, a later migration can switch to content-only IDs after duplicate handling is specified. [ASSUMED]

**Example:**
```python
import hashlib

def make_entry_id(parts: list[str]) -> str:
    normalized = "\n".join(part.strip() for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"shl_{digest}"
```

Source: Requirement requires deterministic ID independent of sparse `编码`; exact hash composition is a planning decision. [VERIFIED: `.planning/REQUIREMENTS.md`]

### Pattern 3: Import Batch Report as First-Class Output

**What:** Store every import as an import batch with counts, warnings, failed rows, and a metadata version. [VERIFIED: `.planning/ROADMAP.md`]

**When to use:** Use this for CLI and later API import because Phase 1 success criteria require visible counts and failure details. [VERIFIED: `.planning/ROADMAP.md`]

**Example report fields:** `total_rows`, `valid_rows`, `skipped_rows`, `warning_count`, `failed_rows`, `indexed_count`, `metadata_version`, `source_file`, and `created_at`. [VERIFIED: `.planning/ROADMAP.md`, `需求文档.md`]

### Anti-Patterns to Avoid

- **Using Excel `编码` as `entry_id`:** `编码` is present in only 32 non-empty data rows, so it cannot be the stable internal ID. [VERIFIED: direct `.xlsx` XML inspection]
- **Dropping raw source columns after normalization:** DATA-02 and ING-04 require all 22 source columns and raw records to remain auditable. [VERIFIED: `.planning/REQUIREMENTS.md`]
- **Auto-splitting every multi-formula row into confident formulas:** The rough formula scan shows many branch labels, slashes, contraindication-like parentheticals, and formula families; ambiguous rows must preserve raw text and can be marked `needs_review`. [VERIFIED: direct `.xlsx` XML inspection]
- **Indexing long evidence fields into `retrieval_text`:** DATA-06 defines a bounded core field set, so long pathology/contraindication/assessment text should remain display/evidence metadata unless later tuning proves otherwise. [VERIFIED: `.planning/REQUIREMENTS.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel parsing | Custom production `.xlsx` XML parser | pandas + openpyxl | Research XML parsing is useful for inspection, but production parsing needs maintained handling of shared strings, empty cells, sheet metadata, and future workbook quirks. [VERIFIED: direct `.xlsx` XML inspection] |
| Data validation | Ad hoc nested dict checks everywhere | Pydantic models and explicit validator functions | Phase 1 contracts later feed API responses and tests. [VERIFIED: `.planning/research/STACK.md`] |
| Local metadata store | Custom flat files as the only source | SQLite tables with optional JSONL export | Import reports and row lookup are query-shaped problems. [ASSUMED] |
| Formula ambiguity resolution | Medical/business truth inference | Conservative parser plus `needs_review` | The workbook contains branch-heavy formula text; automatic clinical interpretation would exceed MVP scope. [VERIFIED: direct `.xlsx` XML inspection, `.planning/REQUIREMENTS.md`] |
| Source schema mapping | Column-position-only logic | Header manifest with required/optional fields | The workbook has title/group rows before actual headers, so position-only parsing is fragile. [VERIFIED: direct `.xlsx` XML inspection] |

**Key insight:** Phase 1 should preserve ambiguity and audit trails rather than forcing perfect formula normalization; later search can rank entries with `formula_raw` and `formula_mentions`, while reviewers can fix `needs_review` rows without data loss. [VERIFIED: `.planning/REQUIREMENTS.md`, direct `.xlsx` XML inspection]

## Common Pitfalls

### Pitfall 1: Header Row Blindness

**What goes wrong:** The importer treats row 1 or row 2 as headers and produces wrong column names. [VERIFIED: direct `.xlsx` XML inspection]  
**Why it happens:** The workbook has a title row, grouped heading row, and actual 22-column header row at row 3. [VERIFIED: direct `.xlsx` XML inspection]  
**How to avoid:** Detect or configure `header_row=3`, then validate all expected header names before importing. [VERIFIED: direct `.xlsx` XML inspection]  
**Warning signs:** Imported records contain empty keys, grouped headings like `四诊合参`, or missing `推荐方剂`. [ASSUMED]

### Pitfall 2: Sparse Codes Becoming Broken Joins

**What goes wrong:** Search results use blank `编码` as the only identifier. [VERIFIED: `.planning/research/SUMMARY.md`]  
**Why it happens:** Only 32 of 1,322 non-empty data rows have `编码`. [VERIFIED: direct `.xlsx` XML inspection]  
**How to avoid:** Return `entry_id` always, keep `source_code` separately, and expose `formula_code: null` with mapping status when unmapped. [VERIFIED: `.planning/REQUIREMENTS.md`]  
**Warning signs:** Duplicate or empty identifiers in import output. [ASSUMED]

### Pitfall 3: Hiding Multi-Formula Ambiguity

**What goes wrong:** One row with several branches is collapsed into one misleading formula. [VERIFIED: direct `.xlsx` XML inspection]  
**Why it happens:** `推荐方剂` cells often include numbered branches, syndrome labels, slashes, or multiple formula names. [VERIFIED: direct `.xlsx` XML inspection]  
**How to avoid:** Preserve `formula_raw`, extract formula mentions conservatively, and mark unresolved branch semantics as `needs_review`. [VERIFIED: `.planning/REQUIREMENTS.md`]  
**Warning signs:** Rows such as row 6 contain multiple syndrome-to-formula mappings but produce a single normalized formula. [VERIFIED: direct `.xlsx` XML inspection]

### Pitfall 4: Non-Rebuildable Retrieval Text

**What goes wrong:** `retrieval_text` is generated imperatively with hidden state and cannot be reproduced from metadata. [ASSUMED]  
**Why it happens:** Field joining is treated as a side effect of indexing rather than Phase 1 data contract. [ASSUMED]  
**How to avoid:** Store normalized core fields and deterministic `retrieval_text` with field labels in a stable order. [VERIFIED: `.planning/REQUIREMENTS.md`, `需求文档.md`]  
**Warning signs:** Re-importing the same row changes `retrieval_text` or ID. [ASSUMED]

## Code Examples

Verified patterns from project requirements and current workbook shape:

### Header Manifest

```python
SOURCE_HEADERS = [
    "编码",
    "人模分类",
    "主干部位",
    "分支部位",
    "主病主症",
    "复合症(适应证)",
    "细分主症",
    "同症异名(方言别名）",
    "人模图示(症状在人体模型上定位显示）",
    "舌诊",
    "脉象",
    "伤寒论原文条文号",
    "中医证型",
    "中医病名",
    "病因（含得病时间 外感 内伤 误治 复发等）",
    "病理",
    "汇通西医病名",
    "中西先后（先看中医？先看西医？）",
    "治法",
    "推荐方剂",
    "推荐方剂配伍中药与西医检查化验指标禁忌",
    "疗效评定",
]
```

Source: actual workbook header row 3. [VERIFIED: direct `.xlsx` XML inspection]

### Retrieval Text Builder

```python
RETRIEVAL_FIELDS = [
    ("部位", ["主干部位", "分支部位"]),
    ("主症", ["主病主症"]),
    ("复合症", ["复合症(适应证)"]),
    ("细分主症", ["细分主症"]),
    ("同症异名", ["同症异名(方言别名）"]),
    ("舌诊", ["舌诊"]),
    ("脉象", ["脉象"]),
    ("证型", ["中医证型"]),
]

def build_retrieval_text(row: dict[str, str]) -> str:
    sections: list[str] = []
    for label, fields in RETRIEVAL_FIELDS:
        values = [row.get(field, "").strip() for field in fields]
        values = [value for value in values if value]
        if values:
            sections.append(f"{label}:\n" + "\n".join(values))
    return "\n\n".join(sections)
```

Source: DATA-06 and requirements document field list. [VERIFIED: `.planning/REQUIREMENTS.md`, `需求文档.md`]

### Conservative Formula Status

```python
import re

AMBIGUITY_PATTERN = re.compile(r"[；;]|(?:^|\s)[一二三四五六七八九十0-9]+[.、]|/|或|偏寒|偏热")

def formula_mapping_status(formula_raw: str, mentions: list[str]) -> str:
    if not formula_raw.strip():
        return "missing"
    if AMBIGUITY_PATTERN.search(formula_raw):
        return "needs_review"
    if mentions:
        return "parsed"
    return "unmapped"
```

Source: formula cells include semicolon branches, numbered branches, slash alternatives, and condition labels. [VERIFIED: direct `.xlsx` XML inspection]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Spreadsheet row equals application record | Canonical record with raw source preservation | Current project requirements | Keeps ingestion auditable and future source adapters possible. [VERIFIED: `.planning/REQUIREMENTS.md`] |
| Source code field as stable ID | Internal deterministic `entry_id` plus separate source/business identifiers | Current project requirements | Prevents sparse source code from breaking search/result joins. [VERIFIED: `.planning/REQUIREMENTS.md`, direct `.xlsx` XML inspection] |
| One formula string equals one formula | Raw formula text plus structured mentions plus review status | Current project requirements | Prevents hidden clinical branch ambiguity. [VERIFIED: `.planning/REQUIREMENTS.md`, direct `.xlsx` XML inspection] |
| Direct customer DB search | Local metadata import and rebuildable indexes | Current MVP scope | Keeps demo independent of unknown MySQL schema. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`] |

**Deprecated/outdated:**
- Treating this phase as Qdrant/BM25 indexing work is out of order; Phase 1 should stop at local metadata and rebuildable normalized records, while indexing starts in Phase 2. [VERIFIED: `.planning/ROADMAP.md`]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLite should be primary metadata storage and JSONL only optional. | Standard Stack, Don't Hand-Roll | Planner may choose a heavier or less queryable persistence design. |
| A2 | Pydantic schemas are preferable to raw dicts/dataclasses for this greenfield service. | Alternatives Considered | Contracts may be duplicated later for API schemas. |
| A3 | Proposed package structure is the best fit. | Architecture Patterns | Planner may need to adapt if a scaffold is introduced before execution. |
| A4 | Stable ID can include source row for v1. | Architecture Patterns | If users require IDs to survive row reordering, use content-only hashing plus duplicate collision handling. |
| A5 | Warning signs and some failure modes are inferred from engineering practice. | Common Pitfalls | Tests may need adjustment once first implementation exists. |

## Open Questions

1. **Should `entry_id` survive row reordering across revised Excel files?** [ASSUMED]
   - What we know: It must be deterministic and independent of sparse `编码`. [VERIFIED: `.planning/REQUIREMENTS.md`]
   - What's unclear: Whether row number is allowed in the hash for MVP. [ASSUMED]
   - Recommendation: Use source row in v1 only if the import report also stores a content fingerprint; otherwise use content fingerprint plus duplicate suffixing. [ASSUMED]

2. **How strict should valid-row criteria be for rows missing formula text?** [ASSUMED]
   - What we know: 76 non-empty rows after the header have empty formula cells, while Phase 1 requires valid/skipped counts. [VERIFIED: direct `.xlsx` XML inspection, `.planning/ROADMAP.md`]
   - What's unclear: Whether such rows should be skipped, stored as non-searchable, or stored as evidence-only. [ASSUMED]
   - Recommendation: Store raw rows, count them as skipped/non-searchable, and include warning details. [ASSUMED]

3. **Does the business team already have a formula-code mapping table?** [ASSUMED]
   - What we know: v1 can return missing formula code with mapping status, and Java backend owns formulary joins. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]
   - What's unclear: Whether Phase 1 should accept an optional mapping file. [ASSUMED]
   - Recommendation: Define the mapping schema now, implement import later unless a mapping file is provided. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Phase 1 runtime | Yes, but below target | 3.9.6 | Use `uv` to create Python 3.12 env. [VERIFIED: `python3 --version`] |
| uv | Dependency/env management | Yes | 0.10.4 | Use supported `uv add`/lock flows; do not rely on unavailable `uv pip index`. [VERIFIED: `uv --version`] |
| pandas | Runtime import parser | No in current global Python | — | Install in project env. [VERIFIED: failed `import pandas`] |
| openpyxl | Runtime `.xlsx` engine | No in current global Python | — | Install in project env. [VERIFIED: failed `import openpyxl`] |
| SQLite CLI | Metadata inspection | Yes | 3.51.0 | Python `sqlite3` stdlib can still write DB. [VERIFIED: `sqlite3 --version`] |
| Docker | Later demo/index phases | Yes | 29.3.0 | Not required for Phase 1 core ingestion. [VERIFIED: `docker --version`] |
| unzip | Research/manual workbook inspection | Yes | 6.00 | Python `zipfile` already works. [VERIFIED: `unzip -v`, direct `.xlsx` XML inspection] |

**Missing dependencies with no fallback:**
- None for planning; implementation must install `pandas` and `openpyxl` in the project environment before writing runtime ingestion code. [VERIFIED: failed imports]

**Missing dependencies with fallback:**
- Global `pandas`/`openpyxl` are missing; fallback for research was direct `.xlsx` ZIP/XML inspection, but production code should install the libraries. [VERIFIED: failed imports, direct `.xlsx` XML inspection]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No for Phase 1 local CLI/storage; yes later for import APIs | Defer API auth to later FastAPI/admin phases. [VERIFIED: Phase 1 scope in `.planning/ROADMAP.md`] |
| V3 Session Management | No | No user sessions in Phase 1. [VERIFIED: Phase 1 scope in `.planning/ROADMAP.md`] |
| V4 Access Control | No for local import; yes later for admin endpoints | Keep local file paths explicit and avoid public import endpoints in Phase 1. [ASSUMED] |
| V5 Input Validation | Yes | Pydantic validation plus header manifest and row-level validation report. [VERIFIED: `.planning/REQUIREMENTS.md`] |
| V6 Cryptography | No | No secrets or cryptographic storage in Phase 1. [VERIFIED: Phase 1 scope in `.planning/ROADMAP.md`] |

### Known Threat Patterns for Phase 1

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed workbook or wrong headers | Tampering | Validate exact header manifest before import. [VERIFIED: direct `.xlsx` XML inspection] |
| Formula/CSV injection in exported audit files | Tampering | Escape leading `=`, `+`, `-`, `@` when producing CSV exports. [ASSUMED] |
| PHI accidentally stored in import logs | Information Disclosure | Phase 1 imports classical knowledge, not patient records; keep logs to file path, counts, row numbers, and validation messages. [VERIFIED: `.planning/PROJECT.md`] |
| Path traversal if future API accepts paths | Tampering | Restrict import path to configured data directory when HTTP import is added. [ASSUMED] |

## Sources

### Primary (HIGH confidence)

- `.planning/STATE.md` - current phase and decisions. [VERIFIED: file read]
- `.planning/ROADMAP.md` - Phase 1 goal, requirements, plans, and success criteria. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - DATA-01..DATA-06 and ING-01..ING-05 definitions. [VERIFIED: file read]
- `.planning/PROJECT.md` - MVP scope, constraints, data source, and out-of-scope boundaries. [VERIFIED: file read]
- `.planning/research/SUMMARY.md` - project-level research, pitfalls, and stack implications. [VERIFIED: file read]
- `需求文档.md` - saved MVP requirements, canonical record sketch, retrieval_text fields, and local metadata options. [VERIFIED: file read]
- `AGENTS.md` - project instructions and GSD workflow constraints. [VERIFIED: file read]
- `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` - workbook shape, headers, row counts, source sparsity, and formula ambiguity scan. [VERIFIED: direct `.xlsx` XML inspection]

### Secondary (MEDIUM confidence)

- PyPI JSON API checks on 2026-06-14 for `pandas`, `openpyxl`, `pydantic`, `pytest`, and `ruff`. [VERIFIED: PyPI JSON API]
- Local tool probes for Python, uv, SQLite, Docker, and unzip. [VERIFIED: shell command output]

### Tertiary (LOW confidence)

- General engineering recommendations around SQLite vs JSONL, package structure, ID hash inputs, and CSV export hardening. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - package versions and project stack were verified, but Python 3.12 setup still needs implementation. [VERIFIED: PyPI JSON API, `.planning/research/STACK.md`]
- Architecture: MEDIUM-HIGH - source-adapter/canonical-model pattern is well aligned with requirements, but repo has no existing code patterns yet. [VERIFIED: repo file scan]
- Pitfalls: HIGH - the largest risks are visible in the actual workbook shape and requirements. [VERIFIED: direct `.xlsx` XML inspection]

**Research date:** 2026-06-14  
**Valid until:** 2026-07-14 for Phase 1 ingestion decisions; re-check package versions before implementation if planning is delayed. [ASSUMED]
