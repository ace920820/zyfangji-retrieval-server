from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FusedCandidate(BaseModel):
    entry_id: str
    bm25_rank: int | None = None
    bm25_score: float | None = None
    vector_rank: int | None = None
    vector_score: float | None = None
    fused_rank: int | None = None
    fused_score: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)


def fuse_candidates(
    bm25_candidates: list[Any],
    vector_candidates: list[Any],
    strategy: str = "rrf",
    rrf_k: int = 60,
    limit: int = 50,
) -> list[FusedCandidate]:
    if strategy not in {"rrf", "weighted"}:
        raise ValueError(f"unsupported fusion strategy: {strategy}")

    candidates: dict[str, FusedCandidate] = {}

    if strategy == "rrf":
        for candidate in bm25_candidates:
            fused = candidates.setdefault(
                candidate.entry_id,
                FusedCandidate(entry_id=candidate.entry_id, payload=_candidate_payload(candidate)),
            )
            fused.bm25_rank = candidate.rank
            fused.bm25_score = candidate.score
            fused.fused_score += 1.0 / (rrf_k + candidate.rank)

        for candidate in vector_candidates:
            fused = candidates.setdefault(
                candidate.entry_id,
                FusedCandidate(entry_id=candidate.entry_id, payload=_candidate_payload(candidate)),
            )
            if not fused.payload:
                fused.payload = _candidate_payload(candidate)
            fused.vector_rank = candidate.rank
            fused.vector_score = candidate.score
            fused.fused_score += 1.0 / (rrf_k + candidate.rank)
    else:
        for candidate in bm25_candidates:
            fused = candidates.setdefault(
                candidate.entry_id,
                FusedCandidate(entry_id=candidate.entry_id, payload=_candidate_payload(candidate)),
            )
            fused.bm25_rank = candidate.rank
            fused.bm25_score = candidate.score
            fused.fused_score += float(candidate.score)
        for candidate in vector_candidates:
            fused = candidates.setdefault(
                candidate.entry_id,
                FusedCandidate(entry_id=candidate.entry_id, payload=_candidate_payload(candidate)),
            )
            fused.vector_rank = candidate.rank
            fused.vector_score = candidate.score
            fused.fused_score += float(candidate.score)

    ordered = sorted(candidates.values(), key=lambda candidate: (-candidate.fused_score, candidate.entry_id))
    for rank, candidate in enumerate(ordered[:limit], start=1):
        candidate.fused_rank = rank
    return ordered[:limit]


def _candidate_payload(candidate: Any) -> dict[str, Any]:
    payload = getattr(candidate, "payload", {}) or {}
    return dict(payload)
