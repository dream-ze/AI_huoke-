"""MVP标签管理路由模块"""

from app.core.database import get_db
from app.schemas.mvp_schemas import TagCreateRequest
from app.services.mvp_tag_service import MvpTagService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/tags")
def list_tags(type: str = Query(None), db: Session = Depends(get_db)):
    """列出标签"""
    svc = MvpTagService(db)
    tags = svc.list_tags(tag_type=type)
    return [
        {"id": t.id, "name": t.name, "type": t.type, "created_at": str(t.created_at) if t.created_at else None}
        for t in tags
    ]


@router.post("/tags")
def create_tag(req: TagCreateRequest, db: Session = Depends(get_db)):
    """创建标签"""
    svc = MvpTagService(db)
    tag = svc.create_tag(req.name, req.type)
    return {"id": tag.id, "name": tag.name, "type": tag.type}
