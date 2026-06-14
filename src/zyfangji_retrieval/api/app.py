from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from zyfangji_retrieval.api.routes.search import router as search_router
from zyfangji_retrieval.api.routes.status import router as status_router
from zyfangji_retrieval.config import AppSettings, get_settings
from zyfangji_retrieval.domain.search_models import SearchError, SearchErrorEnvelope
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore
from zyfangji_retrieval.search.bm25 import BM25Retriever
from zyfangji_retrieval.search.embedding_factory import build_embedding_provider
from zyfangji_retrieval.search.rerank import (
    BGERerankerProvider,
    DeterministicRerankerProvider,
    DisabledRerankerProvider,
    RerankerProvider,
)
from zyfangji_retrieval.search.service import SearchService
from zyfangji_retrieval.search.vector import VectorRetriever


async def _validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": SearchErrorEnvelope(
                error=SearchError(
                    code="validation_error",
                    message="Request validation failed.",
                    details={"errors": exc.errors()},
                )
            ).model_dump(mode="json")
        },
    )


def build_reranker_provider(settings: AppSettings) -> RerankerProvider:
    if settings.reranker_provider == "bge":
        return BGERerankerProvider(model_id=settings.reranker_model_id)
    if settings.reranker_provider == "deterministic":
        return DeterministicRerankerProvider()
    if settings.reranker_provider == "disabled":
        return DisabledRerankerProvider()
    raise ValueError(f"unsupported reranker provider: {settings.reranker_provider}")


def build_search_service(settings: AppSettings) -> SearchService:
    return SearchService(
        settings=settings,
        index_store=SQLiteIndexStateStore(settings.db_path),
        metadata_store=SQLiteMetadataStore(settings.db_path),
        bm25_retriever=BM25Retriever(),
        vector_retriever=VectorRetriever(
            embedding_provider_factory=lambda: build_embedding_provider(settings),
            qdrant_client=QdrantClient(url=settings.qdrant_url),
        ),
        reranker=build_reranker_provider(settings),
    )


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    api = FastAPI(title=resolved_settings.api_title)
    api.state.settings = resolved_settings
    api.state.search_service = build_search_service(resolved_settings)
    api.add_exception_handler(RequestValidationError, _validation_exception_handler)
    api.include_router(status_router)
    api.include_router(search_router)
    return api


app = create_app()
