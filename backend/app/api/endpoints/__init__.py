# Export API endpoints
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.content import router as content_router
from app.api.endpoints.compliance import router as compliance_router
from app.api.endpoints.customer import router as customer_router
from app.api.endpoints.publish import router as publish_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.ai import router as ai_router

__all__ = [
    "auth_router",
    "content_router",
    "compliance_router",
    "customer_router",
    "publish_router",
    "dashboard_router",
    "ai_router",
]
