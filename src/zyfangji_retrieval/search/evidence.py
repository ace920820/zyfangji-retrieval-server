from __future__ import annotations

from typing import Any

from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import (
    EvidenceFields,
    SearchResult,
    SearchResultSource,
    SignalScores,
)
from zyfangji_retrieval.search.fusion import FusedCandidate


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
    "therapy": "治法",
    "tcm_disease": "中医病名",
    "western_disease": "汇通西医病名",
    "contraindication": "推荐方剂配伍中药与西医检查化验指标禁忌",
    "effect": "疗效评定",
    "source_article": "伤寒论原文条文号",
}

WESTERN_MEDICINE_PRIORITY_HEADER = "中西先后（先看中医？先看西医？）"


def project_evidence(entry: KnowledgeEntry) -> EvidenceFields:
    return EvidenceFields(
        main_symptom=_normalized_value(entry, "main_symptom"),
        complex_symptom=_normalized_value(entry, "complex_symptom"),
        detail_symptom=_normalized_value(entry, "detail_symptom"),
        alias=_normalized_value(entry, "alias"),
        tongue=_normalized_value(entry, "tongue"),
        pulse=_normalized_value(entry, "pulse"),
        source_article=_normalized_value(entry, "source_article") or entry.source_article,
        syndrome=_normalized_value(entry, "syndrome"),
        tcm_disease=_normalized_value(entry, "tcm_disease") or entry.tcm_disease,
        western_disease=_normalized_value(entry, "western_disease") or entry.western_disease,
        therapy=_normalized_value(entry, "therapy") or entry.therapy,
        contraindication=_normalized_value(entry, "contraindication") or entry.contraindication,
        effect=_normalized_value(entry, "effect") or entry.effect,
        western_medicine_priority=_optional_str(
            entry.raw_record.get(WESTERN_MEDICINE_PRIORITY_HEADER)
        ),
    )


def project_search_result(
    candidate: FusedCandidate,
    rank: int,
    score_type: str = "rerank_score",
    *,
    entry: KnowledgeEntry,
    retrieval_score: float | None = None,
    rerank_score: float | None = None,
) -> SearchResult:
    score = candidate.fused_score if retrieval_score is None else retrieval_score
    formula_code = _first_formula_code(entry.formula_mentions)
    return SearchResult(
        rank=rank,
        retrieval_score=float(score),
        score_type=score_type,
        entry_id=entry.entry_id,
        source=SearchResultSource(
            book=entry.source_book,
            sheet=entry.source_sheet,
            row=entry.source_row,
            article=entry.source_article,
        ),
        formula_raw=entry.formula_raw,
        formula_mentions=[mention.model_dump(mode="json") for mention in entry.formula_mentions],
        formula_code=formula_code,
        formula_mapping_status=entry.formula_mapping_status,
        evidence=project_evidence(entry),
        signal_scores=SignalScores(
            bm25_score=candidate.bm25_score,
            vector_score=candidate.vector_score,
            fused_score=candidate.fused_score,
            rerank_score=rerank_score,
        ),
    )


def _normalized_value(entry: KnowledgeEntry, key: str) -> str | None:
    value = entry.normalized_record.get(key)
    if value is None:
        source_header = NORMALIZED_FIELD_MAP[key]
        value = entry.raw_record.get(source_header)
    return _optional_str(value)


def _first_formula_code(mentions: list[FormulaMention]) -> str | None:
    for mention in mentions:
        code = _optional_str(mention.code)
        if code is not None:
            return code
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
