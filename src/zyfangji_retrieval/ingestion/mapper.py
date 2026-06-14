from zyfangji_retrieval.domain.ids import make_entry_id
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.ingestion.excel_reader import WorkbookRow
from zyfangji_retrieval.ingestion.formulas import formula_mapping_status, parse_formula_mentions
from zyfangji_retrieval.ingestion.reports import RowIssue
from zyfangji_retrieval.ingestion.retrieval_text import SOURCE_HEADERS, build_retrieval_text


SOURCE_BOOK = "伤寒论"

SEARCHABLE_FIELDS = [
    "主干部位",
    "分支部位",
    "主病主症",
    "复合症(适应证)",
    "细分主症",
    "同症异名(方言别名）",
    "舌诊",
    "脉象",
    "中医证型",
]

EVIDENCE_FIELDS = [
    "伤寒论原文条文号",
    "中医证型",
    "中医病名",
    "治法",
    "推荐方剂配伍中药与西医检查化验指标禁忌",
    "疗效评定",
]

NORMALIZED_FIELD_MAP = {
    "main_part": "主干部位",
    "sub_part": "分支部位",
    "main_symptom": "主病主症",
    "complex_symptom": "复合症(适应证)",
    "detail_symptom": "细分主症",
    "alias": "同症异名(方言别名）",
    "tongue": "舌诊",
    "pulse": "脉象",
    "syndrome": "中医证型",
    "formula": "推荐方剂",
    "therapy": "治法",
    "tcm_disease": "中医病名",
    "western_disease": "汇通西医病名",
    "pathology": "病理",
    "cause": "病因（含得病时间 外感 内伤 误治 复发等）",
    "contraindication": "推荐方剂配伍中药与西医检查化验指标禁忌",
    "effect": "疗效评定",
    "source_article": "伤寒论原文条文号",
    "human_body_image": "人模图示(症状在人体模型上定位显示）",
}


def _source_record(row: WorkbookRow) -> dict[str, str]:
    return {
        header: str(row.raw_record.get(header, "")).strip()
        for header in SOURCE_HEADERS
    }


def validate_source_row(row: WorkbookRow) -> list[RowIssue]:
    raw_record = _source_record(row)
    issues: list[RowIssue] = []

    if not any(raw_record[field] for field in SEARCHABLE_FIELDS):
        issues.append(
            RowIssue(
                source_row=row.source_row,
                code="missing_searchable_text",
                message="At least one searchable symptom, location, tongue, pulse, or syndrome field is required.",
                severity="error",
            )
        )
    if not raw_record["推荐方剂"]:
        issues.append(
            RowIssue(
                source_row=row.source_row,
                code="missing_formula_raw",
                message="推荐方剂 is required for a searchable knowledge entry.",
                severity="error",
            )
        )
    if not any(raw_record[field] for field in EVIDENCE_FIELDS):
        issues.append(
            RowIssue(
                source_row=row.source_row,
                code="missing_evidence",
                message="At least one source evidence, disease, therapy, contraindication, or effect field is required.",
                severity="error",
            )
        )

    mentions = parse_formula_mentions(raw_record["推荐方剂"])
    if formula_mapping_status(raw_record["推荐方剂"], mentions) == "needs_review":
        issues.append(
            RowIssue(
                source_row=row.source_row,
                code="formula_needs_review",
                message="推荐方剂 contains branch or multi-formula text that needs review.",
                severity="warning",
            )
        )

    return issues


def map_row_to_entry(row: WorkbookRow) -> KnowledgeEntry | None:
    issues = validate_source_row(row)
    if any(issue.severity == "error" for issue in issues):
        return None

    raw_record = _source_record(row)
    normalized_record = {
        normalized_key: raw_record[source_key]
        for normalized_key, source_key in NORMALIZED_FIELD_MAP.items()
    }
    formula_mentions = parse_formula_mentions(raw_record["推荐方剂"])
    entry_id = make_entry_id(
        [
            SOURCE_BOOK,
            row.source_sheet,
            str(row.source_row),
            raw_record["伤寒论原文条文号"],
            raw_record["主病主症"],
            raw_record["中医证型"],
            raw_record["推荐方剂"],
        ]
    )

    return KnowledgeEntry(
        entry_id=entry_id,
        source_book=SOURCE_BOOK,
        source_sheet=row.source_sheet,
        source_row=row.source_row,
        source_code=raw_record["编码"] or None,
        formula_raw=raw_record["推荐方剂"],
        formula_mentions=formula_mentions,
        formula_mapping_status=formula_mapping_status(raw_record["推荐方剂"], formula_mentions),
        retrieval_text=build_retrieval_text(raw_record),
        raw_record=raw_record,
        normalized_record=normalized_record,
        therapy=normalized_record["therapy"] or None,
        tcm_disease=normalized_record["tcm_disease"] or None,
        western_disease=normalized_record["western_disease"] or None,
        source_article=normalized_record["source_article"] or None,
        contraindication=normalized_record["contraindication"] or None,
        effect=normalized_record["effect"] or None,
    )
