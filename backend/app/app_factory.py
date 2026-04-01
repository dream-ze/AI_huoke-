import logging
import re
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import jwt
from app.api.router import register_routers
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import BusinessError
from app.core.logging_config import RequestIDFilter, setup_logging
from app.core.metrics import get_user_sequence_metrics_snapshot
from app.services.user_service import UserService
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "desktop" / "dist"
_FRONTEND_INDEX = _FRONTEND_DIR / "index.html"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run best-effort startup checks before serving requests."""
    setup_logging(
        log_level=getattr(settings, "LOG_LEVEL", "INFO"),
        json_format=getattr(settings, "LOG_JSON_FORMAT", True),
    )
    logger.info("Application starting up...")

    if settings.ENABLE_STARTUP_USER_SEQUENCE_HEALTHCHECK:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            UserService.ensure_user_id_sequence_health(db)
        except Exception:
            logger.exception("startup users.id sequence health check failed")
        finally:
            db.close()

    yield


def _extract_user_id(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return "anonymous"

    if auth_header.startswith("Bearer "):
        try:
            payload = jwt.decode(
                auth_header[7:],
                options={"verify_signature": False, "verify_exp": False},
            )
            return payload.get("sub", "unknown")
        except jwt.InvalidTokenError:
            return "invalid_token"
        except Exception:
            return "parse_error"
    return "anonymous"


def _sanitize_path(path: str) -> str:
    if not path:
        return path

    def redact_match(match):
        return f"{match.group(1)}=***"

    return re.sub(
        r"((?:password|token|api_key|secret)\s*[=:])([^&\s]+)",
        redact_match,
        path,
        flags=re.IGNORECASE,
    )


def _register_middlewares(app: FastAPI) -> None:
    cors_origins = settings.CORS_ORIGINS
    allow_credentials = "*" not in cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_tracking_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4())[:8])
        request.state.request_id = request_id
        RequestIDFilter.set_request_id(request_id)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id

        user_id = _extract_user_id(request)
        safe_path = _sanitize_path(request.url.path)

        if not request.url.path.startswith("/health"):
            log_msg = f"{request.method} {safe_path} -> {response.status_code} " f"({duration_ms:.0f}ms) user={user_id}"
            if duration_ms > 3000:
                logger.warning(
                    f"[SLOW_REQUEST] {log_msg}",
                    extra={"request_id": request_id, "duration_ms": duration_ms},
                )
            else:
                logger.info(log_msg, extra={"request_id": request_id})

        RequestIDFilter.clear_request_id()
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数校验失败",
                    "detail": errors,
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"数据库错误: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "数据库操作失败",
                    "detail": None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error(f"未捕获异常: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "detail": None,
                }
            },
        )


def _register_health_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "sequence_metrics": get_user_sequence_metrics_snapshot(),
        }


def _register_frontend_routes(app: FastAPI) -> None:
    if _FRONTEND_DIR.is_dir() and _FRONTEND_INDEX.is_file():
        assets_dir = _FRONTEND_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(str(_FRONTEND_INDEX), media_type="text/html")

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            if full_path.startswith("api/"):
                return HTMLResponse(status_code=404, content='{"detail":"Not Found"}')
            file_path = _FRONTEND_DIR / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(_FRONTEND_INDEX), media_type="text/html")

        return

    @app.get("/")
    def root():
        return {
            "message": "智获客 API（前端未构建，请先执行 cd desktop && npm run build）",
            "version": settings.API_VERSION,
            "docs": "/docs",
        }


def _register_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="智获客 API",
            version=settings.API_VERSION,
            description="AI Content Acquisition System",
            routes=app.routes,
        )
        openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


def create_app() -> FastAPI:
    if settings.DB_AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description="AI Content Acquisition System Backend",
        lifespan=lifespan,
    )

    _register_middlewares(app)
    _register_exception_handlers(app)
    register_routers(app)
    _register_health_routes(app)
    _register_frontend_routes(app)
    _register_openapi(app)
    return app


app = create_app()
