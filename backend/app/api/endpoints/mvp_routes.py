"""
MVP路由汇总模块 - 所有MVP子路由的统一入口
实际路由已拆分到各子模块，此文件负责汇总注册。
"""

from app.api.endpoints.mvp_compliance_routes import router as compliance_router
from app.api.endpoints.mvp_feedback_routes import router as feedback_router
from app.api.endpoints.mvp_generation_routes import router as generation_router
from app.api.endpoints.mvp_inbox_routes import router as inbox_router
from app.api.endpoints.mvp_knowledge_routes import router as knowledge_router
from app.api.endpoints.mvp_material_routes import router as material_router
from app.api.endpoints.mvp_model_routes import router as model_router
from app.api.endpoints.mvp_stats_routes import router as stats_router
from app.api.endpoints.mvp_tag_routes import router as tag_router
from fastapi import APIRouter

# 创建汇总router，保持原有的prefix和tags
router = APIRouter(prefix="/api/mvp", tags=["MVP"])

# 包含所有子路由
router.include_router(inbox_router)
router.include_router(material_router)
router.include_router(knowledge_router)
router.include_router(generation_router)
router.include_router(compliance_router)
router.include_router(stats_router)
router.include_router(feedback_router)
router.include_router(model_router)
router.include_router(tag_router)
