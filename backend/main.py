import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import Base, engine

# Resolve the frontend build directory (desktop/dist)
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "desktop" / "dist"
from app.api.endpoints import (
    auth_router,
    content_router,
    compliance_router,
    customer_router,
    publish_router,
    dashboard_router,
    ai_router,
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI Content Acquisition System Backend",
)

# Add CORS middleware
# When origins=["*"], allow_credentials must be False (Starlette requirement).
# Since auth uses Bearer token in headers, credentials=False is fine.
_cors_origins = settings.CORS_ORIGINS
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(compliance_router)
app.include_router(customer_router)
app.include_router(publish_router)
app.include_router(dashboard_router)
app.include_router(ai_router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# ── Serve frontend static files ─────────────────────────────────
if _FRONTEND_DIR.is_dir():
    # Mount assets with cache-friendly headers
    _assets_dir = _FRONTEND_DIR / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

    @app.get("/")
    async def serve_index():
        """Serve the SPA index.html"""
        return FileResponse(str(_FRONTEND_DIR / "index.html"), media_type="text/html")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA fallback: serve static file if exists, otherwise index.html"""
        file_path = _FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_FRONTEND_DIR / "index.html"), media_type="text/html")
else:
    @app.get("/")
    def root():
        return {
            "message": "智获客 API（前端未构建，请先执行 cd desktop && npm run build）",
            "version": settings.API_VERSION,
            "docs": "/docs",
        }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="智获客 API",
        version=settings.API_VERSION,
        description="AI Content Acquisition System",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
