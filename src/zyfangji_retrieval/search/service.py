from __future__ import annotations

from typing import Any

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.domain.search_models import (
    EvidenceFields,
    PatientSearchRequest,
    QueryWarning,
    SearchPipelineMetadata,
    SearchResponse,
    SearchResult,
    SignalScores,
)
from zyfangji_retrieval.indexing.embeddings import EmbeddingProviderError
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore
from zyfangji_retrieval.search.bm25 import BM25Retriever
from zyfangji_retrieval.search.fusion import FusedCandidate, fuse_candidates
from zyfangji_retrieval.search.query import build_patient_query
from zyfangji_retrieval.search.rerank import (
    RerankCandidate,
    RerankerProvider,
    RerankerProviderError,
)
from zyfangji_retrieval.search.vector import VectorRetriever


class SearchServiceError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class SearchService:
    def __init__(
        self,
        settings: AppSettings,
        index_store: SQLiteIndexStateStore,
        metadata_store: SQLiteMetadataStore,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        reranker: RerankerProvider,
    ) -> None:
        self.settings = settings
        self.index_store = index_store
        self.metadata_store = metadata_store
        self.bm25_retriever = bm25_retriever
        self.vector_retriever = vector_retriever
        self.reranker = reranker

    def search(self, request: PatientSearchRequest) -> SearchResponse:
        patient_query = build_patient_query(request)
        active = self.index_store.get_active()
        self._validate_active(active)
        entries = self.metadata_store.load_entries(index_version=active.metadata_version)
        entries_by_id = {entry.entry_id: entry for entry in entries}

        try:
            bm25_candidates = self.bm25_retriever.recall(
                patient_query.text,
                active=active,
                recall_topk=self.settings.recall_topk,
            )
            vector_candidates = self.vector_retriever.recall(
                patient_query.text,
                active=active,
                recall_topk=self.settings.recall_topk,
            )
        except EmbeddingProviderError as exc:
            raise SearchServiceError(
                code="embedding_provider_unavailable",
                message="Embedding provider is unavailable.",
                details={},
            ) from exc

        fused_candidates = fuse_candidates(
            bm25_candidates,
            vector_candidates,
            strategy=self.settings.fusion_strategy,
            rrf_k=self.settings.rrf_k,
            limit=self.settings.recall_topk,
        )
        warnings = list(patient_query.warnings)
        pipeline_status = "reranked"
        final_order: list[tuple[FusedCandidate, float | None]]

        try:
            reranked = self.reranker.rerank(
                patient_query.text,
                self._rerank_candidates(fused_candidates, entries_by_id),
            )
            rerank_scores = {candidate.entry_id: candidate.rerank_score for candidate in reranked}
            fused_by_id = {candidate.entry_id: candidate for candidate in fused_candidates}
            final_order = [
                (fused_by_id[candidate.entry_id], candidate.rerank_score)
                for candidate in reranked
                if candidate.entry_id in fused_by_id
            ]
        except RerankerProviderError as exc:
            if self.settings.reranker_required:
                raise SearchServiceError(
                    code="reranker_unavailable",
                    message="Reranker provider is unavailable.",
                    details={},
                ) from exc
            warnings.append(
                QueryWarning(
                    code="reranker_degraded",
                    severity="warning",
                    message="Reranker is unavailable; returning fused retrieval ranking.",
                )
            )
            pipeline_status = "reranker_degraded"
            rerank_scores = {}
            final_order = [(candidate, None) for candidate in fused_candidates]

        results = [
            self._result_from_candidate(
                rank=rank,
                candidate=candidate,
                rerank_score=rerank_scores.get(candidate.entry_id),
                entry=entries_by_id.get(candidate.entry_id),
            )
            for rank, (candidate, _score) in enumerate(final_order[: request.topk], start=1)
        ]

        return SearchResponse(
            query_text=patient_query.text,
            results=results,
            warnings=warnings,
            pipeline=SearchPipelineMetadata(
                index_version=active.index_version,
                metadata_version=active.metadata_version,
                recall_topk=self.settings.recall_topk,
                fusion_strategy=self.settings.fusion_strategy,
                reranker_model_id=getattr(self.reranker, "model_id", None),
                pipeline_status=pipeline_status,
            ),
        )

    def _validate_active(self, active: ActiveIndexRecord | None) -> None:
        if (
            active is None
            or not active.index_version
            or not active.metadata_version
            or not active.qdrant_collection
            or not active.bm25_path
            or active.entry_count == 0
            or active.vector_count == 0
            or active.bm25_doc_count == 0
        ):
            raise SearchServiceError(
                code="index_not_ready",
                message="Active retrieval index is not ready.",
                details={},
            )

    def _rerank_candidates(
        self,
        fused_candidates: list[FusedCandidate],
        entries_by_id: dict[str, KnowledgeEntry],
    ) -> list[RerankCandidate]:
        candidates: list[RerankCandidate] = []
        for candidate in fused_candidates:
            entry = entries_by_id.get(candidate.entry_id)
            text = self._candidate_text(candidate, entry)
            candidates.append(
                RerankCandidate(
                    entry_id=candidate.entry_id,
                    text=text,
                    payload=candidate.payload,
                )
            )
        return candidates

    def _candidate_text(self, candidate: FusedCandidate, entry: KnowledgeEntry | None) -> str:
        if entry is not None:
            return entry.retrieval_text
        payload_text = candidate.payload.get("retrieval_text")
        return str(payload_text or "")

    def _result_from_candidate(
        self,
        rank: int,
        candidate: FusedCandidate,
        rerank_score: float | None,
        entry: KnowledgeEntry | None,
    ) -> SearchResult:
        if entry is None:
            evidence = self._evidence_from_payload(candidate.entry_id, candidate.payload)
        else:
            evidence = self._evidence_from_entry(entry)
        match_score = rerank_score if rerank_score is not None else candidate.fused_score
        return SearchResult(
            rank=rank,
            match_score=float(match_score),
            scores=SignalScores(
                bm25_score=candidate.bm25_score,
                vector_score=candidate.vector_score,
                fused_score=candidate.fused_score,
                rerank_score=rerank_score,
            ),
            evidence=evidence,
        )

    def _evidence_from_entry(self, entry: KnowledgeEntry) -> EvidenceFields:
        first_mention = entry.formula_mentions[0] if entry.formula_mentions else None
        return EvidenceFields(
            entry_id=entry.entry_id,
            source_book=entry.source_book,
            source_sheet=entry.source_sheet,
            source_row=entry.source_row,
            formula_name=first_mention.name if first_mention is not None else entry.formula_raw,
            formula_code=first_mention.code if first_mention is not None else entry.source_code,
            formula_mapping_status=entry.formula_mapping_status,
            therapy=entry.therapy,
            tcm_disease=entry.tcm_disease,
            western_disease=entry.western_disease,
            source_article=entry.source_article,
            contraindication=entry.contraindication,
            effect=entry.effect,
            raw_record=entry.raw_record,
            normalized_record=entry.normalized_record,
        )

    def _evidence_from_payload(self, entry_id: str, payload: dict[str, Any]) -> EvidenceFields:
        mentions = payload.get("formula_mentions")
        first_mention = mentions[0] if isinstance(mentions, list) and mentions else {}
        if not isinstance(first_mention, dict):
            first_mention = {}
        formula_raw = str(payload.get("formula_raw") or "")
        return EvidenceFields(
            entry_id=entry_id,
            source_book=str(payload.get("source_book") or ""),
            source_sheet=str(payload.get("source_sheet") or ""),
            source_row=int(payload.get("source_row") or 0),
            formula_name=str(first_mention.get("name") or formula_raw),
            formula_code=first_mention.get("code") or payload.get("source_code"),
            formula_mapping_status=str(payload.get("formula_mapping_status") or "unmapped"),
            therapy=_optional_str(payload.get("therapy")),
            tcm_disease=_optional_str(payload.get("tcm_disease")),
            western_disease=_optional_str(payload.get("western_disease")),
            source_article=_optional_str(payload.get("source_article")),
            contraindication=_optional_str(payload.get("contraindication")),
            effect=_optional_str(payload.get("effect")),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
