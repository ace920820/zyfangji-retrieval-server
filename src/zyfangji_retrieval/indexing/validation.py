from __future__ import annotations

from datetime import UTC, datetime

from zyfangji_retrieval.domain.index_models import IndexValidationResult


def merge_validation_results(
    index_version: str,
    expected_count: int,
    vector_result: IndexValidationResult,
    bm25_result: IndexValidationResult,
) -> IndexValidationResult:
    errors = [*vector_result.errors, *bm25_result.errors]
    return IndexValidationResult(
        index_version=index_version,
        valid=not errors,
        expected_count=expected_count,
        vector_count=vector_result.vector_count,
        bm25_doc_count=bm25_result.bm25_doc_count,
        errors=errors,
        qdrant_collection=vector_result.qdrant_collection,
        qdrant_alias=vector_result.qdrant_alias,
        bm25_path=bm25_result.bm25_path,
        updated_at=datetime.now(UTC),
        last_error="; ".join(errors) if errors else None,
    )


def validate_persisted_counts(
    index_version: str,
    expected_count: int,
    vector_count: int,
    bm25_result: IndexValidationResult,
    qdrant_collection: str | None,
    qdrant_alias: str | None,
) -> IndexValidationResult:
    errors = list(bm25_result.errors)
    if vector_count != expected_count:
        errors.append(f"vector count mismatch: got {vector_count}, expected {expected_count}")
    return IndexValidationResult(
        index_version=index_version,
        valid=not errors,
        expected_count=expected_count,
        vector_count=vector_count,
        bm25_doc_count=bm25_result.bm25_doc_count,
        errors=errors,
        qdrant_collection=qdrant_collection,
        qdrant_alias=qdrant_alias,
        bm25_path=bm25_result.bm25_path,
        updated_at=datetime.now(UTC),
        last_error="; ".join(errors) if errors else None,
    )
