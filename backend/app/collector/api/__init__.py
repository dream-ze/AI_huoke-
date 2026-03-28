"""采集模块 API 路由"""

from app.collector.api.collect_routes import v1_collect_router
from app.collector.api.inbox_routes import v1_inbox_router
from app.collector.api.material_routes import v2_materials_router, materials_routes
from app.collector.api.v2_collect_routes import v2_collect_router, collect_routes

__all__ = [
    "v1_collect_router",
    "v1_inbox_router",
    "v2_collect_router",
    "v2_materials_router",
    "collect_routes",
    "materials_routes",
]