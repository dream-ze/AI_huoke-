from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import DistributedRateLimiter
from app.core.security import verify_token
from app.schemas import (
    AIRewriteRequest,
    ArkVisionRequest,
    ArkVisionResponse,
    PluginContentCreate,
    PluginContentResponse,
)
from app.services import AIService

router = APIRouter(prefix="/api/ai", tags=["ai"])
ark_vision_limiter = DistributedRateLimiter(
    limit=settings.ARK_VISION_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.ARK_VISION_RATE_LIMIT_WINDOW_SECONDS,
    use_redis=settings.USE_REDIS_RATE_LIMIT,
    redis_url=settings.REDIS_URL,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)


_REWRITE_DEPRECATION = {
    "message": "旧 AI 改写接口已下线，请迁移到 /api/v2/materials/{id}/rewrite 或 /api/v1/ai/rewrite/*。",
    "replacement": {
        "materials_rewrite": "/api/v2/materials/{id}/rewrite",
        "v1_rewrite": "/api/v1/ai/rewrite/{platform}",
    },
}


@router.post("/rewrite/xiaohongshu")
async def rewrite_xiaohongshu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
):
    _ = request
    _ = current_user
    raise HTTPException(status_code=410, detail=_REWRITE_DEPRECATION)


@router.post("/rewrite/douyin")
async def rewrite_douyin(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
):
    _ = request
    _ = current_user
    raise HTTPException(status_code=410, detail=_REWRITE_DEPRECATION)


@router.post("/rewrite/zhihu")
async def rewrite_zhihu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
):
    _ = request
    _ = current_user
    raise HTTPException(status_code=410, detail=_REWRITE_DEPRECATION)


@router.post("/plugin/collect", response_model=PluginContentResponse)
def collect_via_plugin(
    plugin_data: PluginContentCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    _ = plugin_data
    _ = current_user
    _ = db
    raise HTTPException(
        status_code=410,
        detail={
            "message": "旧插件采集接口已下线，请迁移到 /api/v1/employee-submissions/link 或 /api/v1/collector/tasks/keyword",
            "replacement": {
                "submission": "/api/v1/employee-submissions/link",
                "keyword_task": "/api/v1/collector/tasks/keyword",
            },
        },
    )


@router.post("/ark/vision", response_model=ArkVisionResponse)
async def ark_vision_analyze(
    request: ArkVisionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Analyze image by Volcano Engine Ark responses API."""
    user_id = str(current_user["user_id"])
    await ark_vision_limiter.check(f"ark_vision:{user_id}")
    ai_service = AIService(db=db)
    return await ai_service.analyze_image_with_ark(
        image_url=request.image_url,
        text=request.text,
        model=request.model,
        user_id=current_user["user_id"],
    )
