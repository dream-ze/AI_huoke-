from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
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
from app.models import BrowserPluginCollection
from app.services.insight_service import InsightService

router = APIRouter(prefix="/api/ai", tags=["ai"])
ark_vision_limiter = DistributedRateLimiter(
    limit=settings.ARK_VISION_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.ARK_VISION_RATE_LIMIT_WINDOW_SECONDS,
    use_redis=settings.USE_REDIS_RATE_LIMIT,
    redis_url=settings.REDIS_URL,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)


@router.post("/rewrite/xiaohongshu")
async def rewrite_xiaohongshu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Rewrite content for Little Red Book"""
    ai_service = AIService(db=db)

    from app.models import ContentAsset
    content = db.query(ContentAsset).filter(ContentAsset.id == request.content_id).first()
    if not content:
        raise Exception("Content not found")

    # 检索洞察库参考上下文
    insight_ctx = None
    if request.topic_name:
        insight_ctx = InsightService.retrieve_for_generation(
            db,
            owner_id=current_user["user_id"],
            platform="xiaohongshu",
            topic_name=request.topic_name,
            audience_tags=request.audience_tags or [],
            limit=5,
        )

    rewritten = await ai_service.rewrite_xiaohongshu(
        content.content,
        request.style or "casual",
        user_id=current_user["user_id"],
        insight_ctx=insight_ctx,
    )

    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "xiaohongshu",
        "insight_used": insight_ctx is not None and (insight_ctx.get("reference_count", 0) > 0),
        "insight_reference_count": insight_ctx.get("reference_count", 0) if insight_ctx else 0,
    }


@router.post("/rewrite/douyin")
async def rewrite_douyin(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Rewrite content for Douyin"""
    ai_service = AIService(db=db)

    from app.models import ContentAsset
    content = db.query(ContentAsset).filter(ContentAsset.id == request.content_id).first()
    if not content:
        raise Exception("Content not found")

    insight_ctx = None
    if request.topic_name:
        insight_ctx = InsightService.retrieve_for_generation(
            db,
            owner_id=current_user["user_id"],
            platform="douyin",
            topic_name=request.topic_name,
            audience_tags=request.audience_tags or [],
            limit=5,
        )

    rewritten = await ai_service.rewrite_douyin(
        content.content,
        user_id=current_user["user_id"],
        insight_ctx=insight_ctx,
    )

    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "douyin",
        "insight_used": insight_ctx is not None and (insight_ctx.get("reference_count", 0) > 0),
        "insight_reference_count": insight_ctx.get("reference_count", 0) if insight_ctx else 0,
    }


@router.post("/rewrite/zhihu")
async def rewrite_zhihu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Rewrite content for Zhihu"""
    ai_service = AIService(db=db)

    from app.models import ContentAsset
    content = db.query(ContentAsset).filter(ContentAsset.id == request.content_id).first()
    if not content:
        raise Exception("Content not found")

    insight_ctx = None
    if request.topic_name:
        insight_ctx = InsightService.retrieve_for_generation(
            db,
            owner_id=current_user["user_id"],
            platform="zhihu",
            topic_name=request.topic_name,
            audience_tags=request.audience_tags or [],
            limit=5,
        )

    rewritten = await ai_service.rewrite_zhihu(
        content.content,
        user_id=current_user["user_id"],
        insight_ctx=insight_ctx,
    )

    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "zhihu",
        "insight_used": insight_ctx is not None and (insight_ctx.get("reference_count", 0) > 0),
        "insight_reference_count": insight_ctx.get("reference_count", 0) if insight_ctx else 0,
    }


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
            "message": "旧插件采集接口已下线，请迁移到 /api/v2/collect/ingest-page",
            "replacement": "/api/v2/collect/ingest-page",
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
