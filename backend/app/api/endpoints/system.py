from fastapi import APIRouter

from app.core.config import settings
from app.core.metrics import get_user_sequence_metrics_snapshot
from app.schemas import SystemVersionResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/version", response_model=SystemVersionResponse)
def get_system_version():
    """Desktop auto-update placeholder endpoint."""
    return {
        "api_version": settings.API_VERSION,
        "app_name": settings.API_TITLE,
        "release_channel": "stable",
        "min_desktop_version": "0.1.0",
        "latest_desktop_version": "0.1.0",
    }


@router.get("/sequence-metrics")
def get_sequence_metrics():
    """Read-only counters for users.id sequence recovery and startup alignment."""
    return get_user_sequence_metrics_snapshot()
