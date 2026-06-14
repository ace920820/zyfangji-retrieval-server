from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.indexing.embeddings import EmbeddingProviderError
from zyfangji_retrieval.search.rerank import RerankCandidate, RerankerProviderError
from zyfangji_retrieval.search.service import SearchService


def _active() -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version="idx-20260614120000",
        metadata_version="meta-20260614120000",
        qdrant_collection="zyfangji_entries_idx_20260614120000",
        qdrant_alias="zyfangji_entries_active",
        bm25_path="/tmp/bm25/idx-20260614120000",
        updated_at=datetime.now(UTC),
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
        retrieval_text="主症:\n发热恶寒\n\n脉象:\n脉浮紧",
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
    def get_active(self) -> ActiveIndexRecord:
        return _active()


class _MetadataStore:
    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        return [
            _entry("entry-1", "麻黄汤", "F-MHT"),
            _entry("entry-2", "桂枝汤", None),
        ]


class _BM25Retriever:
    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        return [
            type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})(),
            type("BM25", (), {"entry_id": "entry-2", "rank": 2, "score": 4.0})(),
        ]


class _VectorRetriever:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        if self.fail:
            raise EmbeddingProviderError("bge_m3 embedding endpoint is not configured")
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

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def rerank(self, query_text: str, candidates: list[RerankCandidate]) -> list[Any]:
        if self.fail:
            raise RerankerProviderError("reranker provider unavailable")
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


def _service(*, vector_fail: bool = False, reranker_fail: bool = False) -> SearchService:
    return SearchService(
        settings=AppSettings(
            recall_topk=50,
            fusion_strategy="rrf",
            rrf_k=60,
            reranker_required=True,
        ),
        index_store=_IndexStore(),
        metadata_store=_MetadataStore(),
        bm25_retriever=_BM25Retriever(),
        vector_retriever=_VectorRetriever(fail=vector_fail),
        reranker=_Reranker(fail=reranker_fail),
    )


def test_search_response_projects_java_friendly_evidence_shape() -> None:
    response = _service().search(PatientSearchRequest(main_symptom="发热恶寒", topk=1))

    payload = response.model_dump(mode="json")
    assert set(payload) == {"query", "results", "warnings", "metadata", "score_semantics"}
    assert payload["query"] == {"text": "主症:\n发热恶寒"}
    assert payload["metadata"]["requested_topk"] == 1
    assert payload["metadata"]["recall_topk"] == 50
    assert payload["metadata"]["pipeline_status"] == "reranked"
    assert "not medical confidence, diagnosis probability, or prescription certainty" in payload[
        "score_semantics"
    ]

    result = payload["results"][0]
    assert set(result) == {
        "rank",
        "retrieval_score",
        "score_type",
        "entry_id",
        "source",
        "formula_raw",
        "formula_mentions",
        "formula_code",
        "formula_mapping_status",
        "evidence",
        "signal_scores",
    }
    assert result["rank"] == 1
    assert result["retrieval_score"] == 0.95
    assert result["score_type"] == "rerank_score"
    assert result["entry_id"] == "entry-1"
    assert result["source"] == {
        "book": "伤寒论",
        "sheet": "病症信息",
        "row": 12,
        "article": "第35条",
    }
    assert result["formula_raw"] == "麻黄汤"
    assert result["formula_mentions"] == [
        {
            "name": "麻黄汤",
            "code": "F-MHT",
            "branch_label": None,
            "needs_review": False,
            "raw_text": None,
        }
    ]
    assert result["formula_code"] == "F-MHT"
    assert result["formula_mapping_status"] == "parsed"
    assert result["signal_scores"] == {
        "bm25_score": 8.0,
        "vector_score": 0.91,
        "fused_score": pytest.approx((1.0 / 61) + (1.0 / 61)),
        "rerank_score": 0.95,
    }
    assert result["evidence"] == {
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
        "western_medicine_priority": "高热不退先看西医",
    }


def test_formula_code_uses_first_non_empty_mention_code() -> None:
    response = _service().search(PatientSearchRequest(main_symptom="发热恶寒", topk=2))

    assert [result.formula_code for result in response.results] == ["F-MHT", None]
