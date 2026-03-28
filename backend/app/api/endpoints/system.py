from datetime import datetime, timezone

import requests
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.metrics import get_user_sequence_metrics_snapshot
from app.schemas import SystemVersionResponse

try:
    import redis
except ImportError:  # pragma: no cover - local fallback outside Poetry env
    redis = None

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


def _probe_database() -> dict:
    started_at = datetime.now(timezone.utc)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return {
            "name": "database",
            "ok": True,
            "dialect": engine.dialect.name,
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return {
            "name": "database",
            "ok": False,
            "dialect": engine.dialect.name,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }


def _probe_redis() -> dict:
    if not settings.USE_REDIS_RATE_LIMIT:
        return {
            "name": "redis",
            "enabled": False,
            "ok": True,
            "message": "USE_REDIS_RATE_LIMIT=False",
        }
    if redis is None:
        return {
            "name": "redis",
            "enabled": True,
            "ok": False,
            "error": "redis package is not installed in current runtime",
        }

    started_at = datetime.now(timezone.utc)
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        pong = client.ping()
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return {
            "name": "redis",
            "enabled": True,
            "ok": bool(pong),
            "elapsed_ms": elapsed_ms,
            "url": settings.REDIS_URL,
        }
    except Exception as exc:
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return {
            "name": "redis",
            "enabled": True,
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "url": settings.REDIS_URL,
            "error": str(exc),
        }


def _probe_ollama() -> dict:
    started_at = datetime.now(timezone.utc)
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags",
            timeout=3,
        )
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models") or []
        return {
            "name": "ollama",
            "ok": True,
            "elapsed_ms": elapsed_ms,
            "base_url": settings.OLLAMA_BASE_URL,
            "model_count": len(models),
            "target_model": settings.OLLAMA_MODEL,
            "target_model_present": any((item.get("name") or "").startswith(settings.OLLAMA_MODEL) for item in models),
        }
    except Exception as exc:
        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return {
            "name": "ollama",
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "base_url": settings.OLLAMA_BASE_URL,
            "target_model": settings.OLLAMA_MODEL,
            "error": str(exc),
        }


@router.get("/ops/health")
def get_ops_health():
    """Operational health view for deployment verification and incident triage."""
    database = _probe_database()
    redis_status = _probe_redis()
    ollama = _probe_ollama()

    checks = {
        "database": database,
        "redis": redis_status,
        "ollama": ollama,
    }
    required_ok = database["ok"] and redis_status["ok"]
    overall_status = "ok" if required_ok and ollama["ok"] else "degraded"

    return {
        "status": overall_status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "sequence_metrics": get_user_sequence_metrics_snapshot(),
        "runtime": {
            "debug": settings.DEBUG,
            "database_host": settings.DATABASE_HOST,
            "database_name": settings.DATABASE_NAME,
            "use_cloud_model": settings.USE_CLOUD_MODEL,
            "redis_rate_limit": settings.USE_REDIS_RATE_LIMIT,
        },
    }


@router.get("/ops/readiness")
def get_ops_readiness():
    """Return 200 only when required runtime dependencies are ready."""
    payload = get_ops_health()
    if payload["checks"]["database"]["ok"] and payload["checks"]["redis"]["ok"]:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
