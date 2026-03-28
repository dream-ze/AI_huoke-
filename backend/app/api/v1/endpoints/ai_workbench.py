from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import DistributedRateLimiter
from app.core.security import verify_token
from app.collector.services.orchestrator import MaterialPipelineOrchestrator
from app.domains.ai_workbench.ai_service import AIService
from app.schemas import (
    AIRewriteRequest,
    ArkVisionRequest,
    ArkVisionResponse,
    PluginContentCreate,
    PluginContentResponse,
)

ai_workbench_routes = APIRouter(tags=["ai-workbench"])
ark_vision_limiter = DistributedRateLimiter(
    limit=settings.ARK_VISION_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.ARK_VISION_RATE_LIMIT_WINDOW_SECONDS,
    use_redis=settings.USE_REDIS_RATE_LIMIT,
    redis_url=settings.REDIS_URL,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)


async def _rewrite_with_material_pipeline(
    request: AIRewriteRequest,
    current_user: dict,
    db: Session,
    platform: str,
) -> dict:
    orchestrator = MaterialPipelineOrchestrator(db=db, owner_id=current_user["user_id"], ai_service=AIService(db=db))
    result = await orchestrator.generate_from_material(
        material_id=request.content_id,
        platform=platform,
        account_type=None,
        target_audience=request.target_audience,
        task_type="rewrite",
    )
    content = result["material"]
    return {
        "original": content.content_text,
        "rewritten": result["output_text"],
        "platform": platform,
        "insight_used": bool(result.get("references")),
        "insight_reference_count": len(result.get("references") or []),
        "references": result.get("references") or [],
        "generation_task_id": result.get("generation_task_id"),
    }


@ai_workbench_routes.post("/rewrite/xiaohongshu")
async def rewrite_xiaohongshu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return await _rewrite_with_material_pipeline(request, current_user, db, "xiaohongshu")


@ai_workbench_routes.post("/rewrite/douyin")
async def rewrite_douyin(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return await _rewrite_with_material_pipeline(request, current_user, db, "douyin")


@ai_workbench_routes.post("/rewrite/zhihu")
async def rewrite_zhihu(
    request: AIRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return await _rewrite_with_material_pipeline(request, current_user, db, "zhihu")


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
