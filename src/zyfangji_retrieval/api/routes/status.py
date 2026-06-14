from fastapi import APIRouter, Depends, HTTPException, Request

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.indexing.status import IndexStatusService
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore


router = APIRouter()


def _get_settings(request: Request) -> AppSettings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("application settings are not configured")
    return settings


def _get_status_service(request: Request) -> IndexStatusService:
    settings = _get_settings(request)
    return IndexStatusService(SQLiteIndexStateStore(settings.db_path), settings)


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status")
def get_status(service: IndexStatusService = Depends(_get_status_service)):
    return service.status()


@router.get("/health/ready")
def health_ready(service: IndexStatusService = Depends(_get_status_service)):
    status = service.status()
    if not status.ready:
        raise HTTPException(status_code=503, detail=status.model_dump(mode="json"))
    return status
