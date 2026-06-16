from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import (
    SCORE_SEMANTICS,
    PatientSearchRequest,
    SearchResponse,
)
from zyfangji_retrieval.indexing.embeddings import EmbeddingProviderError
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry
from zyfangji_retrieval.search.query import build_patient_query
from zyfangji_retrieval.search.rerank import RerankCandidate, RerankerProviderError
from zyfangji_retrieval.search.service import SearchService, SearchServiceError
from zyfangji_retrieval.search.vector import VectorStoreError


SAMPLE_WORKBOOK = Path("data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx")
BANNED_RESPONSE_KEYS = {
    "diagnosis",
    "diagnosis_probability",
    "prescription",
    "prescription_certainty",
    "medical_advice",
    "autonomous_diagnosis",
    "autonomous_prescription",
    "treatment_plan",
    "confidence",
}


def test_workbook_entry_query_and_response_contract_stay_connected() -> None:
    workbook = read_shanghanlun_workbook(SAMPLE_WORKBOOK)
    entry = next(
        mapped
        for row in workbook.rows
        if (mapped := map_row_to_entry(row)) is not None
    )

    assert entry.entry_id.startswith("shl_")
    assert entry.formula_raw
    assert entry.raw_record
    assert entry.normalized_record
    assert "主症:" in entry.retrieval_text or "脉象:" in entry.retrieval_text

    request = PatientSearchRequest(
        main_symptom="头痛",
        symptoms=["发热", "恶风"],
        tongue="舌淡苔白",
        pulse="脉浮紧",
        topk=5,
    )
    query = build_patient_query(request)

    assert "主症:\n头痛" in query.text
    assert "复合症:\n发热\n恶风" in query.text
    assert "舌诊:\n舌淡苔白" in query.text
    assert "脉象:\n脉浮紧" in query.text

    response = _service().search(PatientSearchRequest(main_symptom="头痛", topk=1))

    assert isinstance(response, SearchResponse)
    assert response.results
    assert response.results[0].entry_id == "entry-1"
    assert response.results[0].formula_raw == "麻黄汤"
    assert response.score_semantics == SCORE_SEMANTICS


def test_search_response_foregrounds_evidence_and_omits_generated_medical_fields() -> None:
    payload = _service().search(
        PatientSearchRequest(main_symptom="发热恶寒", pulse="脉浮紧", topk=1)
    ).model_dump(mode="json")

    result = payload["results"][0]
    assert result["source"]["article"] == "第35条"
    assert result["formula_raw"] == "麻黄汤"
    assert result["formula_mentions"][0]["name"] == "麻黄汤"
    assert result["formula_mapping_status"] == "parsed"
    assert result["evidence"]["source_article"] == "第35条"
    assert result["evidence"]["contraindication"] == "阴虚者慎用"
    assert result["evidence"]["western_medicine_priority"] == "高热不退先看西医"
    assert (
        "not medical confidence, diagnosis probability, or prescription certainty"
        in payload["score_semantics"]
    )

    banned_keys = _find_banned_keys(payload, BANNED_RESPONSE_KEYS)
    assert banned_keys == set()


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("embedding", "embedding_provider_unavailable"),
        ("vector_store", "vector_store_unavailable"),
        ("reranker", "reranker_unavailable"),
    ],
)
def test_provider_failure_errors_are_typed_and_do_not_leak_patient_text(
    failure: str,
    expected_code: str,
) -> None:
    service = _service(failure=failure)

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="隐私患者文本"))

    assert error.value.code == expected_code
    assert "隐私患者文本" not in str(error.value)
    assert "隐私患者文本" not in error.value.message
    assert "隐私患者文本" not in str(error.value.details)


def test_missing_active_index_stops_before_partial_results() -> None:
    service = _service(active=None)

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="隐私患者文本"))

    assert error.value.code == "index_not_ready"
    assert "results" not in error.value.details
    assert "隐私患者文本" not in str(error.value)
    assert "隐私患者文本" not in error.value.message


def _find_banned_keys(value: Any, banned: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(key for key in value if key in banned)
        for child in value.values():
            found.update(_find_banned_keys(child, banned))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_banned_keys(child, banned))
    return found


def _active() -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version="idx-20260616000100",
        metadata_version="meta-20260616000100",
        qdrant_collection="zyfangji_entries_idx_20260616000100",
        qdrant_alias="zyfangji_entries_active",
        bm25_path="/tmp/bm25/idx-20260616000100",
        updated_at=datetime.now(UTC),
        activated_at=datetime.now(UTC),
        entry_count=2,
        vector_count=2,
        bm25_doc_count=2,
        provider_id="bge_m3",
        model_id="BAAI/bge-m3",
        vector_size=4,
    )


def _entry(entry_id: str, formula: str, code: str | None) -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_book="伤寒论",
        source_sheet="病症信息",
        source_row=12 if entry_id == "entry-1" else 13,
        source_code=None,
        formula_raw=formula,
        formula_mentions=[FormulaMention(name=formula, code=code)],
        formula_mapping_status="parsed" if code else "unmapped",
        retrieval_text="主症:\n发热恶寒\n\n舌诊:\n舌淡苔白\n\n脉象:\n脉浮紧",
        raw_record={
            "中西先后（先看中医？先看西医？）": "高热不退先看西医",
        },
        normalized_record={
            "main_symptom": "发热恶寒",
            "complex_symptom": "头痛身疼",
            "detail_symptom": "无汗",
            "alias": "伤寒",
            "tongue": "舌淡苔白",
            "pulse": "脉浮紧",
            "source_article": "第35条",
            "syndrome": "太阳伤寒证",
            "tcm_disease": "太阳病",
            "western_disease": "上呼吸道感染",
            "therapy": "发汗解表",
            "contraindication": "阴虚者慎用",
            "effect": "汗出热退",
        },
        therapy="发汗解表",
        tcm_disease="太阳病",
        western_disease="上呼吸道感染",
        source_article="第35条",
        contraindication="阴虚者慎用",
        effect="汗出热退",
    )


class _IndexStore:
    def __init__(self, active: ActiveIndexRecord | None = None) -> None:
        self.active = active

    def get_active(self) -> ActiveIndexRecord | None:
        return self.active


class _MetadataStore:
    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        return [
            _entry("entry-1", "麻黄汤", "F-MHT"),
            _entry("entry-2", "桂枝汤", None),
        ]


class _BM25Retriever:
    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[Any]:
        return [
            type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})(),
            type("BM25", (), {"entry_id": "entry-2", "rank": 2, "score": 4.0})(),
        ]


class _VectorRetriever:
    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure

    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[Any]:
        if self.failure == "embedding":
            raise EmbeddingProviderError("embedding failed while handling 隐私患者文本")
        if self.failure == "vector_store":
            raise VectorStoreError("qdrant failed while handling 隐私患者文本")
        return [
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-1",
                    "rank": 1,
                    "score": 0.91,
                    "payload": {"entry_id": "entry-1"},
                },
            )(),
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-2",
                    "rank": 2,
                    "score": 0.72,
                    "payload": {"entry_id": "entry-2"},
                },
            )(),
        ]


class _Reranker:
    model_id = "BAAI/bge-reranker-v2-m3"

    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure

    def rerank(self, query_text: str, candidates: list[RerankCandidate]) -> list[Any]:
        if self.failure == "reranker":
            raise RerankerProviderError("reranker failed while handling 隐私患者文本")
        scores = {"entry-1": 0.95, "entry-2": 0.2}
        return sorted(
            [
                type(
                    "Reranked",
                    (),
                    {
                        "entry_id": candidate.entry_id,
                        "text": candidate.text,
                        "payload": candidate.payload,
                        "rerank_score": scores[candidate.entry_id],
                    },
                )()
                for candidate in candidates
            ],
            key=lambda candidate: -candidate.rerank_score,
        )


def _service(
    *,
    active: ActiveIndexRecord | None = _active(),
    failure: str | None = None,
) -> SearchService:
    return SearchService(
        settings=AppSettings(
            recall_topk=50,
            fusion_strategy="rrf",
            rrf_k=60,
            reranker_required=True,
        ),
        index_store=_IndexStore(active),
        metadata_store=_MetadataStore(),
        bm25_retriever=_BM25Retriever(),
        vector_retriever=_VectorRetriever(failure),
        reranker=_Reranker(failure),
    )
