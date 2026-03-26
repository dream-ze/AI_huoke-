from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.acquisition.collect_service import CollectService
from app.domains.ai_workbench.ai_service import AIService
from app.models import ContentAsset, ContentInsight


class MaterialUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    tags: Optional[list[str]] = None
    manual_note: Optional[str] = None
    category: Optional[str] = None


class MaterialRewriteRequest(BaseModel):
    target_platform: str = Field(default="xiaohongshu")


materials_routes = APIRouter(prefix="/materials", tags=["materials-v2"])


def _material_row(item: ContentAsset) -> dict[str, Any]:
    blocks = [
        {
            "id": block.id,
            "block_type": block.block_type,
            "block_order": block.block_order,
            "block_text": block.block_text,
        }
        for block in sorted(getattr(item, "blocks", []) or [], key=lambda x: (x.block_order, x.id))
    ]
    comments = [
        {
            "id": comment.id,
            "parent_comment_id": comment.parent_comment_id,
            "commenter_name": comment.commenter_name,
            "comment_text": comment.comment_text,
            "like_count": comment.like_count,
            "is_pinned": bool(comment.is_pinned),
        }
        for comment in (getattr(item, "comments", []) or [])
    ]

    snapshots = sorted(getattr(item, "snapshots", []) or [], key=lambda x: x.id, reverse=True)
    latest_snapshot = snapshots[0] if snapshots else None

    insights = sorted(getattr(item, "insights", []) or [], key=lambda x: x.id, reverse=True)
    latest_insight = insights[0] if insights else None

    if not comments:
        comments = getattr(item, "top_comments", None) or []

    publish_time = getattr(item, "publish_time", None)
    created_at = getattr(item, "created_at", None)
    updated_at = getattr(item, "updated_at", None)
    screenshots = getattr(item, "screenshots", None) or []

    if latest_snapshot is not None:
        snapshot_meta = latest_snapshot.page_meta_json or {}
        snapshot_data = {
            "raw_html": latest_snapshot.raw_html,
            "screenshot_url": latest_snapshot.screenshot_url,
            "page_meta_json": snapshot_meta,
            "raw_payload": snapshot_meta.get("raw_payload") if isinstance(snapshot_meta, dict) else None,
        }
    else:
        snapshot_data = {
            "raw_html": None,
            "screenshot_url": (screenshots or [None])[0],
            "page_meta_json": {},
            "raw_payload": None,
        }

    insight_data = {
        "high_freq_questions_json": latest_insight.high_freq_questions_json if latest_insight else [],
        "key_sentences_json": latest_insight.key_sentences_json if latest_insight else [],
        "title_pattern": latest_insight.title_pattern if latest_insight else None,
        "suggested_topics_json": latest_insight.suggested_topics_json if latest_insight else [],
    }

    return {
        "id": item.id,
        "platform": item.platform,
        "source_type": item.source_type,
        "source_url": item.source_url,
        "content_type": item.content_type,
        "title": item.title,
        "content_text": item.content,
        "author_name": item.author,
        "publish_time": publish_time.isoformat() if publish_time is not None else None,
        "tags": item.tags or [],
        "metrics": item.metrics or {},
        "category": item.category,
        "manual_note": item.manual_note,
        "heat_score": item.heat_score or 0.0,
        "is_viral": bool(item.is_viral),
        "blocks": blocks,
        "comments": comments,
        "snapshot": snapshot_data,
        "insight": insight_data,
        "created_at": created_at.isoformat() if created_at is not None else None,
        "updated_at": updated_at.isoformat() if updated_at is not None else None,
    }


@materials_routes.get("")
def list_materials(
    platform: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_viral: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    items = CollectService.get_list(
        db,
        current_user["user_id"],
        platform=platform,
        category=category,
        is_viral=is_viral,
        search=search,
        skip=skip,
        limit=limit,
    )
    return [_material_row(item) for item in items]


@materials_routes.get("/{material_id}")
def get_material(
    material_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentAsset)
        .filter(ContentAsset.owner_id == current_user["user_id"], ContentAsset.id == material_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")
    return _material_row(item)


@materials_routes.patch("/{material_id}")
def update_material(
    material_id: int,
    req: MaterialUpdateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentAsset)
        .filter(ContentAsset.owner_id == current_user["user_id"], ContentAsset.id == material_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    if req.title is not None:
        setattr(item, "title", req.title)
    if req.content_text is not None:
        setattr(item, "content", req.content_text)
    if req.tags is not None:
        setattr(item, "tags", req.tags)
    if req.manual_note is not None:
        setattr(item, "manual_note", req.manual_note)
    if req.category is not None:
        setattr(item, "category", req.category)

    db.commit()
    db.refresh(item)
    return _material_row(item)


@materials_routes.delete("/{material_id}")
def delete_material(
    material_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentAsset)
        .filter(ContentAsset.owner_id == current_user["user_id"], ContentAsset.id == material_id)
        .first()
    )
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
    item = (
        db.query(ContentAsset)
        .filter(ContentAsset.owner_id == current_user["user_id"], ContentAsset.id == material_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    ai_service = AIService(db=db)
    result = await CollectService.analyze_with_ai(item, ai_service, force_cloud, current_user["user_id"])

    if result.get("tags") is not None:
        setattr(item, "tags", result.get("tags", []))
    if result.get("category") is not None:
        setattr(item, "category", result.get("category"))
    if result.get("heat_score") is not None:
        setattr(item, "heat_score", float(result.get("heat_score", 0.0)))
    if result.get("is_viral") is not None:
        setattr(item, "is_viral", bool(result.get("is_viral", False)))

    high_freq_questions = result.get("viral_reasons") or []
    key_sentences = result.get("key_selling_points") or []
    rewrite_hints = str(result.get("rewrite_hints", "") or "")
    title_pattern = rewrite_hints[:120] if rewrite_hints else None

    insight = (
        db.query(ContentInsight)
        .filter(ContentInsight.content_id == material_id)
        .order_by(ContentInsight.id.desc())
        .first()
    )
    if insight is None:
        insight = ContentInsight(
            content_id=material_id,
            high_freq_questions_json=high_freq_questions,
            key_sentences_json=key_sentences,
            title_pattern=title_pattern,
            suggested_topics_json=[],
        )
        db.add(insight)
    else:
        setattr(insight, "high_freq_questions_json", high_freq_questions)
        setattr(insight, "key_sentences_json", key_sentences)
        setattr(insight, "title_pattern", title_pattern)

    db.commit()

    return {"material_id": material_id, **result}


@materials_routes.post("/{material_id}/rewrite")
async def rewrite_material(
    material_id: int,
    req: MaterialRewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentAsset)
        .filter(ContentAsset.owner_id == current_user["user_id"], ContentAsset.id == material_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    ai_service = AIService(db=db)
    source_text = str(getattr(item, "content", "") or "")
    target = req.target_platform
    if target == "douyin":
        rewritten = await ai_service.rewrite_douyin(source_text, user_id=current_user["user_id"])
    elif target == "zhihu":
        rewritten = await ai_service.rewrite_zhihu(source_text, user_id=current_user["user_id"])
    else:
        rewritten = await ai_service.rewrite_xiaohongshu(source_text, user_id=current_user["user_id"])

    return {
        "material_id": material_id,
        "target_platform": target,
        "original": source_text,
        "rewritten": rewritten,
    }


v2_materials_router = APIRouter()
v2_materials_router.include_router(materials_routes)
