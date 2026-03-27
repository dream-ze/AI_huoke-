from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.ai_workbench.ai_service import AIService
from app.models import GenerationTask, KnowledgeDocument, MaterialItem
from app.services.collector import AcquisitionIntakeService


class MaterialUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    review_note: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[str] = None


class MaterialRewriteRequest(BaseModel):
    target_platform: str = Field(default="xiaohongshu")
    account_type: Optional[str] = None
    target_audience: Optional[str] = None
    task_type: str = Field(default="rewrite")


materials_routes = APIRouter(prefix="/materials", tags=["materials-v2"])


def _knowledge_document_row(document: KnowledgeDocument) -> dict[str, Any]:
    chunks = sorted(document.knowledge_chunks or [], key=lambda item: item.chunk_index)
    return {
        "document_id": document.id,
        "platform": document.platform,
        "account_type": document.account_type,
        "target_audience": document.target_audience,
        "content_type": document.content_type,
        "topic": document.topic,
        "title": document.title,
        "summary": document.summary,
        "content_text": document.content_text,
        "chunks": [chunk.chunk_text for chunk in chunks],
        "chunk_keywords": [chunk.keywords or [] for chunk in chunks],
    }


def _generation_task_row(task: GenerationTask) -> dict[str, Any]:
    created_at = getattr(task, "created_at", None)
    return {
        "generation_task_id": task.id,
        "platform": task.platform,
        "account_type": task.account_type,
        "target_audience": task.target_audience,
        "task_type": task.task_type,
        "output_text": task.output_text,
        "reference_document_ids": task.reference_document_ids or [],
        "created_at": created_at.isoformat() if created_at else None,
    }


def _material_row(item: MaterialItem, include_detail: bool = False) -> dict[str, Any]:
    payload = AcquisitionIntakeService.serialize_material_item(item, include_raw_data=include_detail)
    primary_doc = AcquisitionIntakeService.get_primary_knowledge_document(item)
    payload.update(
        {
            "source_url": payload.pop("url", None),
            "author_name": payload.pop("author", None),
            "content_text": payload.pop("content", None),
            "hot_level": item.hot_level,
            "lead_level": item.lead_level,
            "knowledge": {
                "document_id": primary_doc.id if primary_doc else None,
                "account_type": primary_doc.account_type if primary_doc else None,
                "target_audience": primary_doc.target_audience if primary_doc else None,
                "content_type": primary_doc.content_type if primary_doc else None,
                "topic": primary_doc.topic if primary_doc else None,
                "summary": primary_doc.summary if primary_doc else None,
                "chunk_count": len(primary_doc.knowledge_chunks or []) if primary_doc else 0,
            },
            "generation_count": len(item.generation_tasks or []),
        }
    )
    if include_detail:
        documents = sorted(item.knowledge_documents or [], key=lambda value: value.id)
        generations = sorted(item.generation_tasks or [], key=lambda value: value.id, reverse=True)
        payload["knowledge_documents"] = [_knowledge_document_row(document) for document in documents]
        payload["generation_tasks"] = [_generation_task_row(task) for task in generations[:10]]
    return payload


@materials_routes.get("")
def list_materials(
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_status: Optional[str] = Query(None),
    source_channel: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    items = AcquisitionIntakeService.list_inbox(
        db=db,
        owner_id=current_user["user_id"],
        status=status,
        platform=platform,
        source_channel=source_channel,
        keyword=search,
        risk_status=risk_status,
        skip=skip,
        limit=limit,
    )
    return [_material_row(item, include_detail=False) for item in items]


@materials_routes.get("/{material_id}")
def get_material(
    material_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = AcquisitionIntakeService.get_material_item(db, current_user["user_id"], material_id)
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")
    return _material_row(item, include_detail=True)


@materials_routes.patch("/{material_id}")
def update_material(
    material_id: int,
    req: MaterialUpdateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = AcquisitionIntakeService.get_material_item(db, current_user["user_id"], material_id)
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    if req.title is not None:
        setattr(item, "title", req.title)
    if req.content_text is not None:
        setattr(item, "content_text", req.content_text)
        setattr(item, "content_preview", req.content_text[:100])
        normalized = item.normalized_content
        if normalized is not None:
            setattr(normalized, "content_text", req.content_text)
            setattr(normalized, "content_preview", req.content_text[:100])
    if req.review_note is not None:
        setattr(item, "review_note", req.review_note)
    if req.remark is not None:
        setattr(item, "remark", req.remark)
    if req.status is not None:
        setattr(item, "status", req.status)

    db.commit()
    db.refresh(item)
    return _material_row(item)


@materials_routes.delete("/{material_id}")
def delete_material(
    material_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = AcquisitionIntakeService.get_material_item(db, current_user["user_id"], material_id)
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    db.delete(item)
    db.commit()
    return {"message": "已删除"}


@materials_routes.post("/{material_id}/analyze")
async def analyze_material(
    material_id: int,
    force_cloud: bool = Query(False),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    _ = force_cloud
    try:
        return AcquisitionIntakeService.reindex_material(db, current_user["user_id"], material_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@materials_routes.post("/{material_id}/rewrite")
async def rewrite_material(
    material_id: int,
    req: MaterialRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    ai_service = AIService(db=db)
    item = AcquisitionIntakeService.get_material_item(db, current_user["user_id"], material_id)
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    primary_doc = AcquisitionIntakeService.get_primary_knowledge_document(item)
    account_type = req.account_type or (primary_doc.account_type if primary_doc else "科普号")
    target_audience = req.target_audience or (primary_doc.target_audience if primary_doc else "泛人群")
    return await AcquisitionIntakeService.generate(
        db=db,
        owner_id=current_user["user_id"],
        material_id=material_id,
        platform=req.target_platform,
        account_type=account_type,
        target_audience=target_audience,
        task_type=req.task_type,
        ai_service=ai_service,
    )


v2_materials_router = APIRouter()
v2_materials_router.include_router(materials_routes)
