from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

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
