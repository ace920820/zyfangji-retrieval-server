from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.search.rerank import RerankCandidate
from zyfangji_retrieval.search.service import SearchService


P50_THRESHOLD_MS = 500
P95_THRESHOLD_MS = 1000


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.queries)
    requests = [PatientSearchRequest.model_validate(case["request"]) for case in cases]

    if args.mode == "live" and not args.base_url:
        print("--base-url is required when --mode live", file=sys.stderr)
        return 2

    runner = _live_runner(args.base_url) if args.mode == "live" else _offline_runner()

    for request in requests * args.warmups:
        runner(request)

    samples: list[float] = []
    for _ in range(args.runs):
        for request in requests:
            started = time.perf_counter()
            runner(request)
            samples.append((time.perf_counter() - started) * 1000)

    active = runner.active if isinstance(runner, _OfflineRunner) else None
    report = _build_report(
        mode=args.mode,
        query_count=len(requests),
        warmup_count=len(requests) * args.warmups,
        samples=samples,
        active=active,
    )
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))

    if args.enforce_thresholds and not report["thresholds_passed"]:
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure warm /api/search latency with offline deterministic or live HTTP execution.",
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
        help="offline uses deterministic in-process search; live posts to --base-url /api/search.",
    )
    parser.add_argument(
        "--base-url",
        help="Base URL for live mode, for example http://127.0.0.1:8000.",
    )
    parser.add_argument("--runs", type=int, default=20, help="Measured runs per query.")
    parser.add_argument("--warmups", type=int, default=3, help="Warmup runs per query before measuring.")
    parser.add_argument(
        "--enforce-thresholds",
        action="store_true",
        help="Exit non-zero when p50_ms >= 500 or p95_ms >= 1000.",
    )
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.warmups < 0:
        parser.error("--warmups must be >= 0")
    return args


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _offline_runner() -> "_OfflineRunner":
    return _OfflineRunner(_offline_service())


def _live_runner(base_url: str | None) -> "_LiveRunner":
    if not base_url:
        raise ValueError("base_url is required")
    return _LiveRunner(base_url)


def _build_report(
    *,
    mode: str,
    query_count: int,
    warmup_count: int,
    samples: list[float],
    active: ActiveIndexRecord | None,
) -> dict[str, Any]:
    p50_ms = _percentile(samples, 0.50)
    p95_ms = _percentile(samples, 0.95)
    max_ms = max(samples) if samples else 0.0
    thresholds_passed = p50_ms < P50_THRESHOLD_MS and p95_ms < P95_THRESHOLD_MS
    return {
        "mode": mode,
        "query_count": query_count,
        "sample_count": len(samples),
        "warmup_count": warmup_count,
        "p50_ms": round(p50_ms, 3),
        "p95_ms": round(p95_ms, 3),
        "max_ms": round(max_ms, 3),
        "thresholds": {"p50_ms": P50_THRESHOLD_MS, "p95_ms": P95_THRESHOLD_MS},
        "thresholds_passed": thresholds_passed,
        "dataset_size": active.entry_count if active else None,
        "index_version": active.index_version if active else None,
        "metadata_version": active.metadata_version if active else None,
    }


def _percentile(samples: list[float], percentile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = max(0, int(len(ordered) * percentile + 0.999999) - 1)
    return ordered[min(index, len(ordered) - 1)]


class _OfflineRunner:
    def __init__(self, service: SearchService) -> None:
        self.service = service
        self.active = service.index_store.get_active()

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
            raise RuntimeError(f"live search failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"live search failed: {exc.reason}") from exc


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


if __name__ == "__main__":
    raise SystemExit(main())
