from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import DistributedRateLimiter
from app.core.security import verify_token
from app.domains.acquisition.collect_service import CollectService
from app.domains.ai_workbench.ai_service import AIService
from app.models import BrowserPluginCollection, ContentAsset
from app.schemas import (
    AIRewriteRequest,
    ArkVisionRequest,
    ArkVisionResponse,
    PluginContentCreate,
    PluginContentResponse,
)
from app.services.insight_service import InsightService

ai_workbench_routes = APIRouter(tags=["ai-workbench"])
ark_vision_limiter = DistributedRateLimiter(
    limit=settings.ARK_VISION_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.ARK_VISION_RATE_LIMIT_WINDOW_SECONDS,
    use_redis=settings.USE_REDIS_RATE_LIMIT,
    redis_url=settings.REDIS_URL,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)


def _sync_plugin_content_asset(
    db: Session,
    user_id: int,
    plugin_data: PluginContentCreate,
) -> ContentAsset:
    existing = (
        db.query(ContentAsset)
        .filter(
            ContentAsset.owner_id == user_id,
            ContentAsset.source_url == plugin_data.url,
        )
        .first()
    )
    if existing:
        return existing

    comment_count = len(plugin_data.comments_json or [])
    asset = ContentAsset(
        owner_id=user_id,
        platform=plugin_data.platform,
        source_url=plugin_data.url,
        content_type="post",
        title=plugin_data.title,
        content=plugin_data.content,
        author=plugin_data.author,
        publish_time=plugin_data.publish_time,
        tags=plugin_data.tags or [],
        metrics={"comment_count": comment_count},
        heat_score=float(plugin_data.heat_score or 0.0),
        is_viral=bool((plugin_data.heat_score or 0.0) >= 80),
        source_type="plugin",
        category=CollectService.auto_category(plugin_data.title, plugin_data.content),
        manual_note="浏览器插件采集自动入库",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@ai_workbench_routes.post("/rewrite/xiaohongshu")
async def rewrite_xiaohongshu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
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


@ai_workbench_routes.post("/rewrite/douyin")
async def rewrite_douyin(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
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


@ai_workbench_routes.post("/rewrite/zhihu")
async def rewrite_zhihu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
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


@ai_workbench_routes.post("/plugin/collect", response_model=PluginContentResponse)
def collect_via_plugin(
    plugin_data: PluginContentCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
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


@ai_workbench_routes.post("/ark/vision", response_model=ArkVisionResponse)
async def ark_vision_analyze(
    request: ArkVisionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user_id = str(current_user["user_id"])
    await ark_vision_limiter.check(f"ark_vision:{user_id}")
    ai_service = AIService(db=db)
    return await ai_service.analyze_image_with_ark(
        image_url=request.image_url,
        text=request.text,
        model=request.model,
        user_id=current_user["user_id"],
    )


v1_ai_workbench_router = APIRouter(prefix="/ai")
v1_ai_workbench_router.include_router(ai_workbench_routes)
