from fastapi import APIRouter, Depends
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
    
    # Get original content
    from app.models import ContentAsset
    content = db.query(ContentAsset).filter(ContentAsset.id == request.content_id).first()
    if not content:
        raise Exception("Content not found")
    
    rewritten = await ai_service.rewrite_xiaohongshu(
        content.content,
        request.style or "casual",
        user_id=current_user["user_id"],
    )
    
    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "xiaohongshu"
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
    
    rewritten = await ai_service.rewrite_douyin(content.content, user_id=current_user["user_id"])
    
    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "douyin"
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
    
    rewritten = await ai_service.rewrite_zhihu(content.content, user_id=current_user["user_id"])
    
    return {
        "original": content.content,
        "rewritten": rewritten,
        "platform": "zhihu"
    }


@router.post("/plugin/collect", response_model=PluginContentResponse)
def collect_via_plugin(
    plugin_data: PluginContentCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Collect content via browser plugin"""
    collection = BrowserPluginCollection(
        user_id=current_user["user_id"],
        **plugin_data.model_dump()
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


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
