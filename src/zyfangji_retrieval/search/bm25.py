from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.indexing.bm25_store import BM25IndexStore
from zyfangji_retrieval.indexing.tokenizer import tokenize_chinese_text


class BM25RecallCandidate(BaseModel):
    entry_id: str
    rank: int
    score: float


class BM25Retriever:
    def __init__(
        self,
        index_store_factory: Callable[[Path], BM25IndexStore] = BM25IndexStore,
    ) -> None:
        self.index_store_factory = index_store_factory

    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[BM25RecallCandidate]:
        store = self.index_store_factory(Path(active.bm25_path).parent)
        self._last_store = store
        snapshot = store.load(active.index_version)
        tokens = tokenize_chinese_text(query_text)
        results, scores = snapshot.index.retrieve(
            [tokens],
            corpus=snapshot.metadata.entry_ids,
            k=recall_topk,
            show_progress=False,
        )
        entry_ids = list(results[0]) if results else []
        raw_scores = list(scores[0]) if scores else []
        return [
            BM25RecallCandidate(entry_id=str(entry_id), rank=rank, score=float(score))
            for rank, (entry_id, score) in enumerate(zip(entry_ids, raw_scores, strict=False), start=1)
        ]
