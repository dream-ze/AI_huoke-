from app.api.v1.endpoints.collect import v1_collect_router
from app.api.v1.endpoints.ai_workbench import v1_ai_workbench_router
from app.api.v1.endpoints.inbox import v1_inbox_router

__all__ = [
    "v1_collect_router",
    "v1_ai_workbench_router",
    "v1_inbox_router",
]
