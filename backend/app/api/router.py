from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.compliance import router as compliance_router
from app.api.endpoints.content import router as content_router
from app.api.endpoints.conversation import router as conversation_router
from app.api.endpoints.customer import router as customer_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.insight import router as insight_router
from app.api.endpoints.lead import router as lead_router
from app.api.endpoints.mvp_routes import router as mvp_router
from app.api.endpoints.platform_rule_routes import router as platform_rule_router
from app.api.endpoints.publish import router as publish_router
from app.api.endpoints.reminder import router as reminder_router
from app.api.endpoints.social_account import router as social_account_router
from app.api.endpoints.system import router as system_router
from app.api.endpoints.topic import router as topic_router
from app.api.endpoints.traffic import router as traffic_router
from app.api.endpoints.wecom import router as wecom_router
from app.api.v1 import api_v1_router
from app.api.v2 import api_v2_router
from fastapi import FastAPI

ALL_ROUTERS = (
    auth_router,
    content_router,
    compliance_router,
    customer_router,
    lead_router,
    publish_router,
    dashboard_router,
    insight_router,
    system_router,
    wecom_router,
    mvp_router,
    social_account_router,
    reminder_router,
    conversation_router,
    traffic_router,
    topic_router,
    platform_rule_router,
    api_v1_router,
    api_v2_router,
)


def register_routers(app: FastAPI) -> None:
    for router in ALL_ROUTERS:
        app.include_router(router)
