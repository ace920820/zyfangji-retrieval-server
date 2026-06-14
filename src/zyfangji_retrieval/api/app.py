from fastapi import FastAPI

from zyfangji_retrieval.api.routes.status import router as status_router
from zyfangji_retrieval.config import AppSettings, get_settings


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    api = FastAPI(title=resolved_settings.api_title)
    api.state.settings = resolved_settings
    api.include_router(status_router)
    return api


app = create_app()
