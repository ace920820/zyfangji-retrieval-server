from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.search.rerank import RerankCandidate
from zyfangji_retrieval.search.service import SearchService


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.queries)
    requests = [PatientSearchRequest.model_validate(case["request"]) for case in cases]
    runner = _live_runner(args.base_url) if args.mode == "live" else _offline_runner()

    rows: list[dict[str, Any]] = []
    for case, request in zip(cases, requests, strict=True):
        payload = runner(request)
        results = payload.get("results", [])[: args.limit]
        row = {
            "id": case["id"],
            "category": case["category"],
            "query": payload.get("query", {}),
            "results": [
                {
                    "formula_raw": result.get("formula_raw"),
                    "source_article": result.get("evidence", {}).get("source_article"),
                    "pipeline_status": payload.get("metadata", {}).get("pipeline_status"),
                }
                for result in results
            ],
            "warnings": [warning.get("code") for warning in payload.get("warnings", [])],
            "score_semantics": "Retrieval scores are relative ranking/reference signals only.",
        }
        rows.append(row)

    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "query_count": len(requests),
                    "results": rows,
                    "score_semantics": "Retrieval scores are relative ranking/reference signals only.",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        for row in rows:
            print(f"{row['id']} [{row['category']}]")
            print(f"  warnings: {', '.join(row['warnings']) or 'none'}")
            print(f"  score semantics: {row['score_semantics']}")
            for result in row["results"]:
                article = result["source_article"] or "-"
                print(f"  - {result['formula_raw']} | {article}")

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reviewer smoke demo over offline fixture or live /api/search."
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("tests/fixtures/smoke_queries.json"),
        help="Path to smoke query fixture JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=("offline", "live"),
        default="offline",
        help="offline uses deterministic in-process demo behavior; live posts to --base-url /api/search.",
    )
    parser.add_argument("--base-url", help="Base URL for live mode, for example http://127.0.0.1:8000.")
    parser.add_argument("--limit", type=int, default=3, help="Max results to show per query.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be >= 1")
    if args.mode == "live" and not args.base_url:
        parser.error("--base-url is required when --mode live")
    return args


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _offline_runner() -> "_OfflineRunner":
    return _OfflineRunner(_offline_service())


def _live_runner(base_url: str | None) -> "_LiveRunner":
    if not base_url:
        raise ValueError("base_url is required")
    return _LiveRunner(base_url)


class _OfflineRunner:
    def __init__(self, service: SearchService) -> None:
        self.service = service

    def __call__(self, request: PatientSearchRequest) -> dict[str, Any]:
        return self.service.search(request).model_dump(mode="json")


class _LiveRunner:
    def __init__(self, base_url: str) -> None:
        self.url = f"{base_url.rstrip('/')}/api/search"

    def __call__(self, request: PatientSearchRequest) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        http_request = Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"live demo failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"live demo failed: {exc.reason}") from exc


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
        raw_record={"中西先后（先看中医？先看西医？）": "高热不退先看西医"},
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
                retrieval_text="主症:\n头痛 发热 恶风 无汗\n\n脉象:\n脉浮紧\n\n舌诊:\n舌淡苔白",
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
                retrieval_text="主症:\n发热 恶风\n\n脉象:\n脉浮缓\n\n舌诊:\n舌淡",
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
                retrieval_text="主症:\n往来寒热\n\n脉象:\n脉弦\n\n舌诊:\n舌苔薄白",
                main_symptom="往来寒热",
                pulse="脉弦",
                tongue="舌苔薄白",
                syndrome="少阳病",
                contraindication="过敏者慎用",
            ),
        ]


class _BM25Retriever:
    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        scores = _rank_scores(query_text)
        return [
            type("BM25", (), {"entry_id": entry_id, "rank": rank, "score": score})()
            for rank, (entry_id, score) in enumerate(scores, start=1)
        ]


class _VectorRetriever:
    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
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
    model_id = "deterministic-demo-reranker"

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


if __name__ == "__main__":
    raise SystemExit(main())
