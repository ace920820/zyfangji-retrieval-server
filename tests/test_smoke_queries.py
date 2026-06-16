from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.search.rerank import RerankCandidate
from zyfangji_retrieval.search.service import SearchService


SMOKE_FIXTURE_PATH = Path("tests/fixtures/smoke_queries.json")


def _smoke_cases() -> list[dict[str, Any]]:
    return json.loads(SMOKE_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_smoke_query_fixture_requests_are_valid() -> None:
    for case in _smoke_cases():
        PatientSearchRequest.model_validate(case["request"])
        assert case["expect"]["min_results"] >= 1
        assert case["expect"]["banned_fields"]


@pytest.mark.parametrize("case", _smoke_cases(), ids=lambda case: case["id"])
def test_smoke_queries_return_ranked_safe_offline_results(case: dict[str, Any]) -> None:
    request = PatientSearchRequest.model_validate(case["request"])
    response = _offline_service().search(request)
    payload = response.model_dump(mode="json")
    expect = case["expect"]

    assert len(response.results) >= expect["min_results"], case["id"]
    assert "not medical confidence, diagnosis probability, or prescription certainty" in response.score_semantics
    assert _find_banned_keys(payload, set(expect["banned_fields"])) == set(), case["id"]

    for field_path in expect.get("must_have_fields", []):
        assert _path_exists(payload, field_path), f"{case['id']} missing {field_path}"

    expected_warnings = set(expect.get("must_have_warnings", []))
    warning_codes = {warning["code"] for warning in payload["warnings"]}
    assert expected_warnings <= warning_codes, case["id"]

    expected_formulas = set(expect.get("must_include_any_formula", []))
    if expected_formulas:
        returned_formulas = _returned_formula_names(payload)
        assert expected_formulas & returned_formulas, case["id"]


def _path_exists(payload: dict[str, Any], field_path: str) -> bool:
    values: list[Any] = [payload]
    for part in field_path.split("."):
        next_values: list[Any] = []
        for value in values:
            if isinstance(value, dict) and part in value:
                next_values.append(value[part])
            elif isinstance(value, list):
                if part.isdigit():
                    index = int(part)
                    if index < len(value):
                        next_values.append(value[index])
                else:
                    next_values.extend(item.get(part) for item in value if isinstance(item, dict) and part in item)
        values = [value for value in next_values if value not in (None, "", [])]
        if not values:
            return False
    return True


def _find_banned_keys(value: Any, banned_fields: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(key for key in value if key in banned_fields)
        for child in value.values():
            found.update(_find_banned_keys(child, banned_fields))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_banned_keys(child, banned_fields))
    return found


def _returned_formula_names(payload: dict[str, Any]) -> set[str]:
    formulas: set[str] = set()
    for result in payload["results"]:
        formulas.add(result["formula_raw"])
        for mention in result["formula_mentions"]:
            name = mention.get("name")
            if name:
                formulas.add(name)
    return formulas


def _offline_service() -> SearchService:
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
        vector_retriever=_VectorRetriever(),
        reranker=_DeterministicReranker(),
    )


def _active() -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version="idx-smoke",
        metadata_version="meta-smoke",
        qdrant_collection="zyfangji_entries_idx_smoke",
        qdrant_alias="zyfangji_entries_active",
        bm25_path="/tmp/bm25/idx-smoke",
        updated_at=datetime.now(UTC),
        activated_at=datetime.now(UTC),
        entry_count=3,
        vector_count=3,
        bm25_doc_count=3,
        provider_id="deterministic",
        model_id="deterministic-bge-m3-compatible",
        vector_size=4,
    )


def _entry(
    entry_id: str,
    *,
    formula: str,
    article: str,
    retrieval_text: str,
    main_symptom: str,
    pulse: str,
    tongue: str,
    syndrome: str,
    contraindication: str,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_book="伤寒论",
        source_sheet="病症信息",
        source_row=int(entry_id.rsplit("-", maxsplit=1)[-1]),
        source_code=None,
        formula_raw=formula,
        formula_mentions=[FormulaMention(name=formula, code=f"F-{entry_id}")],
        formula_mapping_status="parsed",
        retrieval_text=retrieval_text,
        raw_record={
            "中西先后（先看中医？先看西医？）": "高热不退先看西医",
        },
        normalized_record={
            "main_symptom": main_symptom,
            "complex_symptom": "头痛 发热 恶风 无汗",
            "detail_symptom": "无汗",
            "alias": "伤寒",
            "tongue": tongue,
            "pulse": pulse,
            "source_article": article,
            "syndrome": syndrome,
            "tcm_disease": "太阳病",
            "western_disease": "上呼吸道感染",
            "therapy": "发汗解表",
            "contraindication": contraindication,
            "effect": "汗出热退",
        },
        therapy="发汗解表",
        tcm_disease="太阳病",
        western_disease="上呼吸道感染",
        source_article=article,
        contraindication=contraindication,
        effect="汗出热退",
    )


class _IndexStore:
    def get_active(self) -> ActiveIndexRecord:
        return _active()


class _MetadataStore:
    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        return [
            _entry(
                "entry-1",
                formula="麻黄汤",
                article="第35条",
                retrieval_text="头痛 发热 恶风 无汗 脉浮紧 舌淡苔白 麻黄汤 第35条 太阳伤寒证",
                main_symptom="头痛",
                pulse="脉浮紧",
                tongue="舌淡苔白",
                syndrome="太阳伤寒证",
                contraindication="阴虚者慎用",
            ),
            _entry(
                "entry-2",
                formula="桂枝汤",
                article="第12条",
                retrieval_text="发热 恶风 汗出 脉浮缓 桂枝汤 太阳中风证",
                main_symptom="发热恶风",
                pulse="脉浮缓",
                tongue="舌淡",
                syndrome="太阳中风证",
                contraindication="表实无汗者慎用",
            ),
            _entry(
                "entry-3",
                formula="小柴胡汤",
                article="第96条",
                retrieval_text="往来寒热 胸胁苦满 口苦 小柴胡汤 少阳病",
                main_symptom="往来寒热",
                pulse="脉弦",
                tongue="舌苔薄白",
                syndrome="少阳病",
                contraindication="过敏者慎用",
            ),
        ]


class _BM25Retriever:
    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[Any]:
        scores = _rank_scores(query_text)
        return [
            type("BM25", (), {"entry_id": entry_id, "rank": rank, "score": score})()
            for rank, (entry_id, score) in enumerate(scores, start=1)
        ]


class _VectorRetriever:
    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[Any]:
        scores = _rank_scores(query_text)
        return [
            type(
                "Vector",
                (),
                {
                    "entry_id": entry_id,
                    "rank": rank,
                    "score": score / 10.0,
                    "payload": {"entry_id": entry_id},
                },
            )()
            for rank, (entry_id, score) in enumerate(scores, start=1)
        ]


class _DeterministicReranker:
    model_id = "deterministic-smoke-reranker"

    def rerank(self, query_text: str, candidates: list[RerankCandidate]) -> list[Any]:
        scores = dict(_rank_scores(query_text))
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
            key=lambda candidate: (-candidate.rerank_score, candidate.entry_id),
        )


def _rank_scores(query_text: str) -> list[tuple[str, float]]:
    entry_terms = {
        "entry-1": ["头痛", "发热", "恶风", "无汗", "脉浮紧", "舌淡苔白", "麻黄汤", "第35条", "太阳伤寒证", "寒"],
        "entry-2": ["发热", "恶风", "脉浮缓", "桂枝汤", "太阳中风证", "寒"],
        "entry-3": ["往来寒热", "小柴胡汤", "少阳病", "寒"],
    }
    scored = []
    for entry_id, terms in entry_terms.items():
        score = sum(1.0 for term in terms if term in query_text)
        scored.append((entry_id, score or 0.1))
    return sorted(scored, key=lambda item: (-item[1], item[0]))
