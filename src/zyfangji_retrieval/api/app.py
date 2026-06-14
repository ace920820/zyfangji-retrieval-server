from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from zyfangji_retrieval.api.routes.search import router as search_router
from zyfangji_retrieval.api.routes.status import router as status_router
from zyfangji_retrieval.config import AppSettings, get_settings
from zyfangji_retrieval.domain.search_models import SearchError, SearchErrorEnvelope


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


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    api = FastAPI(title=resolved_settings.api_title)
    api.state.settings = resolved_settings
    api.add_exception_handler(RequestValidationError, _validation_exception_handler)
    api.include_router(status_router)
    api.include_router(search_router)
    return api


app = create_app()
