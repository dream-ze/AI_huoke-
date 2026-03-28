from fastapi import APIRouter

from app.api.v1.endpoints.ai_workbench import v1_ai_workbench_router
from app.api.v1.endpoints.collect import v1_collect_router
from app.api.v1.endpoints.copy import v1_copy_router
from app.api.v1.endpoints.inbox import v1_inbox_router
from app.api.v1.endpoints.submissions import v1_integrations_router, v1_submissions_router

api_v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

api_v1_router.include_router(v1_collect_router)
api_v1_router.include_router(v1_ai_workbench_router)
api_v1_router.include_router(v1_inbox_router)
api_v1_router.include_router(v1_submissions_router)
api_v1_router.include_router(v1_integrations_router)
api_v1_router.include_router(v1_copy_router)


@api_v1_router.get("/health")
def v1_health() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}
