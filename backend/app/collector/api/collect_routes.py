from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.collector.services.pipeline import AcquisitionIntakeService
from app.models import CollectTask, MaterialItem

v1_collect_router = APIRouter(prefix="/collector", tags=["collector-v1"])


class KeywordTaskCreateRequest(BaseModel):
    platform: str = Field(min_length=2, max_length=30)
    keyword: str = Field(min_length=1, max_length=255)
    max_items: int = Field(default=20, ge=1, le=100)


class SearchCollectRequest(BaseModel):
    """搜索采集请求"""
    platform: str = Field(min_length=2, max_length=30, description="目标平台")
    keyword: str = Field(min_length=1, max_length=255, description="搜索关键词")
    max_items: int = Field(default=20, ge=1, le=100, description="最大采集数量")


class ImportLinkRequest(BaseModel):
    """链接导入请求"""
    url: str = Field(min_length=5, max_length=1000, description="内容链接")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")


class ImportManualRequest(BaseModel):
    """手工导入请求"""
    platform: str = Field(default="xiaohongshu", min_length=2, max_length=30, description="平台")
    title: str = Field(min_length=1, max_length=500, description="标题")
    content: str = Field(min_length=1, description="内容")
    tags: list[str] = Field(default=[], description="标签列表")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")


@v1_collect_router.post("/tasks/keyword")
def create_keyword_task(
    req: KeywordTaskCreateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """创建关键词采集任务"""
    try:
        return AcquisitionIntakeService.create_keyword_task(
            db=db,
            owner_id=current_user["user_id"],
            platform=req.platform,
            keyword=req.keyword,
            max_items=req.max_items,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"调用采集服务失败: {exc}") from exc


@v1_collect_router.post("/search")
def search_collect(
    req: SearchCollectRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """搜索采集 - 按关键词搜索并采集内容"""
    try:
        return AcquisitionIntakeService.create_keyword_task(
            db=db,
            owner_id=current_user["user_id"],
            platform=req.platform,
            keyword=req.keyword,
            max_items=req.max_items,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"搜索采集失败: {exc}") from exc


@v1_collect_router.post("/import-link")
def import_link(
    req: ImportLinkRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """链接导入 - 通过链接导入单条内容"""
    try:
        return AcquisitionIntakeService.submit_link(
            db=db,
            owner_id=current_user["user_id"],
            employee_id=current_user["user_id"],
            url=req.url,
            note=req.note,
            source_type="manual_link",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"链接导入失败: {exc}") from exc


@v1_collect_router.post("/import-manual")
def import_manual(
    req: ImportManualRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """手工导入 - 手动录入内容"""
    try:
        return AcquisitionIntakeService.submit_manual(
            db=db,
            owner_id=current_user["user_id"],
            platform=req.platform,
            title=req.title,
            content=req.content,
            tags=req.tags,
            note=req.note,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"手工导入失败: {exc}") from exc


@v1_collect_router.get("/tasks")
def list_tasks(
    status: Optional[str] = Query(default=None, description="任务状态：pending/success/failed"),
    platform: Optional[str] = Query(default=None, description="平台"),
    skip: int = Query(default=0, ge=0, description="跳过条数"),
    limit: int = Query(default=50, ge=1, le=200, description="返回条数"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """采集任务列表"""
    query = db.query(CollectTask).filter(CollectTask.owner_id == current_user["user_id"])
    if status:
        query = query.filter(CollectTask.status == status)
    if platform:
        query = query.filter(CollectTask.platform == platform)
    tasks = query.order_by(desc(CollectTask.created_at)).offset(skip).limit(limit).all()
    return [
        {
            "id": t.id,
            "task_type": t.task_type,
            "platform": t.platform,
            "keyword": t.keyword,
            "max_items": t.max_items,
            "status": t.status,
            "result_count": t.result_count,
            "inserted_count": t.inserted_count,
            "review_count": t.review_count,
            "discard_count": t.discard_count,
            "duplicate_count": t.duplicate_count,
            "failed_count": t.failed_count,
            "error_message": t.error_message,
            "created_at": str(t.created_at) if t.created_at else None,
        }
        for t in tasks
    ]


@v1_collect_router.get("/results")
def list_results(
    status: Optional[str] = Query(default=None, description="素材状态：pending/review/discard"),
    platform: Optional[str] = Query(default=None, description="平台"),
    keyword: Optional[str] = Query(default=None, description="关键词"),
    skip: int = Query(default=0, ge=0, description="跳过条数"),
    limit: int = Query(default=50, ge=1, le=200, description="返回条数"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """采集结果列表 - 返回素材库中的采集内容"""
    items = AcquisitionIntakeService.list_inbox(
        db=db,
        owner_id=current_user["user_id"],
        status=status,
        platform=platform,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    return [
        {
            "id": item.id,
            "platform": item.platform,
            "title": item.title,
            "content_preview": (item.content_text or "")[:200] if item.content_text else "",
            "author_name": item.author_name,
            "source_url": item.source_url,
            "keyword": item.keyword,
            "status": item.status,
            "risk_status": item.risk_status,
            "is_duplicate": item.is_duplicate,
            "like_count": item.like_count,
            "comment_count": item.comment_count,
            "created_at": str(item.created_at) if item.created_at else None,
        }
        for item in items
    ]
