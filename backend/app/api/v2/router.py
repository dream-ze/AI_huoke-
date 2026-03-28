from fastapi import APIRouter

from app.collector.api.v2_collect_routes import v2_collect_router
from app.collector.api.material_routes import v2_materials_router

api_v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

api_v2_router.include_router(v2_collect_router)
api_v2_router.include_router(v2_materials_router)


@api_v2_router.get("/health")
def v2_health() -> dict[str, str]:
    return {"status": "ok", "version": "v2"}
