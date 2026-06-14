from typing import Protocol

from fastapi import APIRouter, HTTPException, Request

from zyfangji_retrieval.domain.search_models import (
    PatientSearchRequest,
    SearchError,
    SearchErrorEnvelope,
    SearchResponse,
)
from zyfangji_retrieval.search.service import SearchServiceError


class SearchService(Protocol):
    def search(self, request: PatientSearchRequest) -> SearchResponse: ...


router = APIRouter()

SERVICE_UNAVAILABLE_CODES = {
    "index_not_ready",
    "vector_store_unavailable",
    "embedding_provider_unavailable",
    "reranker_unavailable",
}


def _get_search_service(request: Request) -> SearchService:
    service = getattr(request.app.state, "search_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail=SearchErrorEnvelope(
                error=SearchError(
                    code="search_service_unavailable",
                    message="Search service is not configured.",
                    details={},
                )
            ).model_dump(mode="json"),
        )
    return service


@router.post(
    "/api/search",
    response_model=SearchResponse,
    responses={503: {"model": SearchErrorEnvelope}, 422: {"model": SearchErrorEnvelope}},
)
def search(
    request: PatientSearchRequest,
    raw_request: Request,
) -> SearchResponse:
    service = _get_search_service(raw_request)
    try:
        return service.search(request)
    except SearchServiceError as exc:
        status_code = 503 if exc.code in SERVICE_UNAVAILABLE_CODES else 500
        code = exc.code if exc.code in SERVICE_UNAVAILABLE_CODES else "search_internal_error"
        raise HTTPException(
            status_code=status_code,
            detail=SearchErrorEnvelope(
                error=SearchError(
                    code=code,
                    message=exc.message,
                    details=exc.details,
                )
            ).model_dump(mode="json"),
        ) from exc
