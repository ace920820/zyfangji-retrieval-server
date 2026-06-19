from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from zyfangji_retrieval.indexing.tokenizer import tokenize_chinese_text


class RerankCandidate(BaseModel):
    entry_id: str
    text: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RerankedCandidate(RerankCandidate):
    rerank_score: float = 0.0
    rerank_rank: int | None = None


class RerankerProvider(Protocol):
    model_id: str

    def rerank(self, query_text: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]:
        ...


class RerankerProviderError(RuntimeError):
    pass


class BGERerankerProvider:
    def __init__(
        self,
        model_id: str | None = None,
        reranker: Any | None = None,
        reranker_loader: Callable[[], Any] | None = None,
    ) -> None:
        self.model_id = model_id or "BAAI/bge-reranker-v2-m3"
        self._reranker = reranker
        self._reranker_loader = reranker_loader

    def _get_reranker(self) -> Any:
        if self._reranker is not None:
            return self._reranker
        try:
            loader = self._reranker_loader or self._default_loader
            reranker_cls = loader()
            if self.model_id == "BAAI/bge-reranker-v2-m3":
                self._reranker = reranker_cls("BAAI/bge-reranker-v2-m3", use_fp16=True)
            else:
                self._reranker = reranker_cls(self.model_id, use_fp16=True)
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise RerankerProviderError("reranker provider unavailable") from exc
        return self._reranker

    def _default_loader(self) -> Any:
        try:
            from FlagEmbedding import FlagReranker
        except Exception as exc:  # pragma: no cover - import boundary
            raise RerankerProviderError("reranker provider unavailable") from exc
        return FlagReranker

    def rerank(self, query_text: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]:
        reranker = self._get_reranker()
        try:
            scores = reranker.compute_score([[query_text, candidate.text] for candidate in candidates])
        except Exception as exc:
            raise RerankerProviderError("reranker provider unavailable") from exc
        parsed_scores = _coerce_scores(scores, len(candidates))
        reranked = [
            RerankedCandidate(
                **candidate.model_dump(),
                rerank_score=score,
            )
            for candidate, score in zip(candidates, parsed_scores, strict=True)
        ]
        reranked.sort(key=lambda candidate: (-candidate.rerank_score, candidate.entry_id))
        for rank, candidate in enumerate(reranked, start=1):
            candidate.rerank_rank = rank
        return reranked


class SiliconFlowRerankerProvider:
    def __init__(
        self,
        endpoint_url: str,
        api_key: str | None,
        model_id: str = "BAAI/bge-reranker-v2-m3",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not endpoint_url:
            raise RerankerProviderError("silicon reranker endpoint is not configured")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client()

    def rerank(self, query_text: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]:
        candidate_list = list(candidates)
        if not candidate_list:
            return []
        try:
            response = self.client.post(
                self.endpoint_url,
                json={
                    "model": self.model_id,
                    "query": query_text,
                    "documents": [candidate.text for candidate in candidate_list],
                    "return_documents": False,
                },
                headers=(
                    {"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key
                    else None
                ),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            raise RerankerProviderError("reranker provider unavailable") from exc

        if getattr(response, "status_code", 500) < 200 or getattr(response, "status_code", 500) >= 300:
            raise RerankerProviderError("reranker provider unavailable")

        try:
            payload = response.json()
            scores_by_index = self._parse_scores(payload, len(candidate_list))
        except RerankerProviderError:
            raise
        except Exception as exc:
            raise RerankerProviderError("reranker score output is malformed") from exc

        reranked = [
            RerankedCandidate(
                **candidate.model_dump(),
                rerank_score=scores_by_index[index],
            )
            for index, candidate in enumerate(candidate_list)
        ]
        reranked.sort(key=lambda candidate: (-candidate.rerank_score, candidate.entry_id))
        for rank, candidate in enumerate(reranked, start=1):
            candidate.rerank_rank = rank
        return reranked

    def _parse_scores(self, payload: Any, expected_count: int) -> dict[int, float]:
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise RerankerProviderError("reranker score output is malformed")
        scores_by_index: dict[int, float] = {}
        for item in payload["results"]:
            if not isinstance(item, dict):
                raise RerankerProviderError("reranker score output is malformed")
            try:
                index = int(item["index"])
                score = item.get("relevance_score", item.get("score"))
                scores_by_index[index] = float(score)
            except (KeyError, TypeError, ValueError) as exc:
                raise RerankerProviderError("reranker score output is malformed") from exc
        if set(scores_by_index) != set(range(expected_count)):
            raise RerankerProviderError("reranker score count mismatch")
        return scores_by_index


class DeterministicRerankerProvider:
    model_id = "BAAI/bge-reranker-v2-m3"

    def rerank(self, query_text: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]:
        query_tokens = set(tokenize_chinese_text(query_text))
        reranked = []
        for candidate in candidates:
            candidate_tokens = set(tokenize_chinese_text(candidate.text))
            overlap = len(query_tokens & candidate_tokens)
            score = float(overlap) + (0.1 if query_text and query_text in candidate.text else 0.0)
            reranked.append(
                RerankedCandidate(
                    **candidate.model_dump(),
                    rerank_score=score,
                )
            )
        reranked.sort(key=lambda candidate: (-candidate.rerank_score, candidate.entry_id))
        for rank, candidate in enumerate(reranked, start=1):
            candidate.rerank_rank = rank
        return reranked


class DisabledRerankerProvider:
    model_id = None

    def rerank(self, query_text: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]:
        raise RerankerProviderError("reranker is disabled")


def _coerce_scores(scores: Any, expected_count: int) -> list[float]:
    if expected_count == 0:
        return []
    if isinstance(scores, (int, float)):
        return [float(scores)]
    if hasattr(scores, "tolist"):
        scores = scores.tolist()
    if isinstance(scores, tuple):
        scores = list(scores)
    if not isinstance(scores, list):
        scores = [scores]
    if len(scores) != expected_count:
        raise RerankerProviderError(
            f"reranker score count mismatch: got {len(scores)} scores for {expected_count} candidates"
        )
    coerced: list[float] = []
    for score in scores:
        if hasattr(score, "tolist"):
            score = score.tolist()
        if isinstance(score, list):
            if len(score) != 1:
                raise RerankerProviderError("reranker score output is malformed")
            score = score[0]
        try:
            coerced.append(float(score))
        except (TypeError, ValueError) as exc:
            raise RerankerProviderError("reranker score output is malformed") from exc
    return coerced
