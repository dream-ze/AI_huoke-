"""MVP收件箱路由模块"""

from app.core.config import settings
from app.core.database import get_db
from app.schemas.mvp_schemas import BatchIdsRequest, IngestRequest
from app.services.cleaning_service import CleaningService
from app.services.extraction_service import ExtractionService
from app.services.mvp_inbox_service import MvpInboxService
from app.services.pipeline_service import PipelineService
from app.services.quality_screening_service import QualityScreeningService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/inbox")
def list_inbox(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    platform: str = Query(None),
    source_type: str = Query(None),
    risk_level: str = Query(None),
    duplicate_status: str = Query(None),
    keyword: str = Query(None),
    clean_status: str = Query(None),
    quality_status: str = Query(None),
    risk_status: str = Query(None),
    material_status: str = Query(None),
    db: Session = Depends(get_db),
):
    """列出收件箱条目，支持筛选和分页"""
    svc = MvpInboxService(db)
    result = svc.list_inbox(
        page=page,
        size=size,
        status=status,
        platform=platform,
        source_type=source_type,
        risk_level=risk_level,
        duplicate_status=duplicate_status,
        keyword=keyword,
        clean_status=clean_status,
        quality_status=quality_status,
        risk_status=risk_status,
        material_status=material_status,
    )
    # 序列化items - 包含所有新字段
    items_out = []
    for item in result.get("items", []):
        items_out.append(
            {
                "id": item.id,
                "platform": item.platform,
                "source_id": item.source_id,
                "title": item.title,
                "content": item.content,
                "content_preview": item.content_preview,
                "author": item.author,
                "author_name": item.author_name,
                "source_url": item.source_url,
                "source_type": item.source_type,
                "keyword": item.keyword,
                "risk_level": item.risk_level,
                "duplicate_status": item.duplicate_status,
                "score": item.score,
                "quality_score": item.quality_score,
                "risk_score": item.risk_score,
                "tech_status": item.tech_status,
                "biz_status": item.biz_status,
                "clean_status": item.clean_status,
                "quality_status": item.quality_status,
                "risk_status": item.risk_status,
                "material_status": item.material_status,
                "like_count": item.like_count,
                "comment_count": item.comment_count,
                "favorite_count": item.favorite_count,
                "publish_time": str(item.publish_time) if item.publish_time else None,
                "cleaned_at": str(item.cleaned_at) if item.cleaned_at else None,
                "screened_at": str(item.screened_at) if item.screened_at else None,
                "created_at": str(item.created_at) if item.created_at else None,
                "updated_at": str(item.updated_at) if item.updated_at else None,
            }
        )
    return {
        "items": items_out,
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "size": result.get("size", size),
    }


@router.get("/inbox/{item_id}")
def get_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """获取单条收件箱条目"""
    svc = MvpInboxService(db)
    item = svc.get_item(item_id)
    if not item:
        raise HTTPException(404, "收件箱条目不存在")
    return {
        "id": item.id,
        "platform": item.platform,
        "title": item.title,
        "content": item.content,
        "author": item.author,
        "source_url": item.source_url,
        "source_type": item.source_type,
        "keyword": item.keyword,
        "risk_level": item.risk_level,
        "duplicate_status": item.duplicate_status,
        "score": item.score,
        "tech_status": item.tech_status,
        "biz_status": item.biz_status,
        "created_at": str(item.created_at) if item.created_at else None,
    }


@router.post("/inbox/{item_id}/to-material")
async def inbox_to_material(item_id: int, db: Session = Depends(get_db)):
    """将收件箱条目入素材库（使用 PipelineService）"""
    service = PipelineService(db)
    result = await service.promote_to_material(item_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/inbox/{item_id}/mark-hot")
def inbox_mark_hot(item_id: int, db: Session = Depends(get_db)):
    """标记收件箱条目为爆款"""
    try:
        svc = MvpInboxService(db)
        item = svc.mark_hot(item_id)
        return {"message": "已标记爆款", "score": item.score}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/inbox/{item_id}/discard")
def inbox_discard(item_id: int, db: Session = Depends(get_db)):
    """丢弃收件箱条目"""
    try:
        svc = MvpInboxService(db)
        svc.discard(item_id)
        return {"message": "已废弃"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/inbox/{item_id}/ignore")
async def ignore_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条忽略 - 更新 material_status='ignored'"""
    from app.models.models import MvpInboxItem

    item = db.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.material_status = "ignored"
    db.commit()
    return {"success": True, "item_id": item_id}


@router.post("/inbox/{item_id}/clean")
def clean_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条收件箱条目清洗"""
    service = CleaningService(db)
    result = service.clean_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Clean failed"))
    return result


@router.post("/inbox/batch-clean")
def batch_clean_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量清洗收件箱条目"""
    service = CleaningService(db)
    stats = service.batch_clean(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", []),
    }


@router.post("/inbox/{item_id}/screen")
async def screen_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条质量筛选"""
    extraction_svc = ExtractionService(ollama_base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    service = QualityScreeningService(db, extraction_service=extraction_svc)
    result = await service.screen_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/inbox/batch-screen")
async def batch_screen_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量质量筛选"""
    extraction_svc = ExtractionService(ollama_base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    service = QualityScreeningService(db, extraction_service=extraction_svc)
    stats = await service.batch_screen(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", []),
    }


@router.post("/inbox/ingest")
async def ingest_to_inbox(request: IngestRequest, db: Session = Depends(get_db)):
    """采集数据入收件箱（自动触发清洗）"""
    service = PipelineService(db)
    return await service.ingest_from_collector(request.model_dump())


@router.post("/inbox/batch-to-material")
async def batch_to_material(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量入素材库"""
    service = PipelineService(db)
    stats = await service.batch_promote_to_material(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", []),
    }


@router.post("/inbox/batch-ignore")
async def batch_ignore_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量忽略"""
    service = PipelineService(db)
    stats = await service.batch_ignore(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", []),
    }
