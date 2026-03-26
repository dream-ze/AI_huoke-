from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.acquisition.collect_service import CollectService, PLATFORM_LABELS
from app.models import ContentAsset, ContentBlock, ContentComment, ContentSnapshot


class ExtractFromUrlRequest(BaseModel):
    url: str


class CollectBlockIn(BaseModel):
    block_type: str = "paragraph"
    block_order: int = 0
    block_text: str


class CollectCommentIn(BaseModel):
    comment_text: str
    commenter_name: Optional[str] = None
    like_count: int = 0
    is_pinned: bool = False
    parent_comment_id: Optional[int] = None


class CollectSnapshotIn(BaseModel):
    raw_html: Optional[str] = None
    screenshot_url: Optional[str] = None
    page_meta_json: dict[str, Any] = Field(default_factory=dict)


class IngestPageRequest(BaseModel):
    source_type: str = "manual_link"
    client_request_id: Optional[str] = Field(default=None, min_length=8, max_length=128)
    platform: str
    source_url: Optional[str] = None
    content_type: str = "post"
    title: str
    content_text: str
    author_name: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    blocks: list[CollectBlockIn] = Field(default_factory=list)
    comments: list[CollectCommentIn] = Field(default_factory=list)
    snapshot: Optional[CollectSnapshotIn] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    manual_note: Optional[str] = None


class SpiderXHSNoteIn(BaseModel):
    note_id: str
    note_url: Optional[str] = None
    note_type: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    nickname: Optional[str] = None
    upload_time: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    liked_count: int = 0
    collected_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    image_list: list[str] = Field(default_factory=list)
    video_cover: Optional[str] = None
    video_addr: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class SpiderXHSBatchIn(BaseModel):
    items: list[SpiderXHSNoteIn] = Field(default_factory=list, min_length=1, max_length=200)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    # Try common Spider_XHS output formats first.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    # Fallback for ISO-like timestamps.
    iso = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def _split_blocks(text: str) -> list[CollectBlockIn]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    blocks: list[CollectBlockIn] = []
    for idx, line in enumerate(lines[:100], start=1):
        block_type = "heading" if len(line) <= 24 else "paragraph"
        blocks.append(CollectBlockIn(block_type=block_type, block_order=idx, block_text=line))
    return blocks


def _build_spider_ingest_request(req: SpiderXHSNoteIn) -> IngestPageRequest:
    content_text = (req.desc or "").strip() or (req.title or "").strip() or "Spider_XHS 导入内容"
    title = (req.title or "").strip() or (content_text[:40] if content_text else "无标题")
    is_video = "视频" in (req.note_type or "") or bool(req.video_addr)
    screenshot_url = req.video_cover or (req.image_list[0] if req.image_list else None)
    raw_payload = req.raw_payload or req.model_dump()

    return IngestPageRequest(
        source_type="crawler_spider_xhs",
        client_request_id=f"spiderxhs-{req.note_id}",
        platform="xiaohongshu",
        source_url=req.note_url,
        content_type="video" if is_video else "post",
        title=title,
        content_text=content_text,
        author_name=req.nickname,
        publish_time=_parse_datetime(req.upload_time),
        tags=req.tags or [],
        metrics={
            "like_count": int(req.liked_count or 0),
            "favorite_count": int(req.collected_count or 0),
            "comment_count": int(req.comment_count or 0),
            "share_count": int(req.share_count or 0),
        },
        blocks=_split_blocks(content_text),
        comments=[],
        snapshot=CollectSnapshotIn(
            raw_html=None,
            screenshot_url=screenshot_url,
            page_meta_json={
                "crawler": "Spider_XHS",
                "note_type": req.note_type,
                "video_addr": req.video_addr,
                "image_count": len(req.image_list or []),
                "raw_payload": raw_payload,
            },
        ),
        raw_payload=raw_payload,
        manual_note="Spider_XHS crawler import",
    )


collect_routes = APIRouter(prefix="/collect", tags=["collect-v2"])


def _to_log_row(item: ContentAsset) -> dict[str, Any]:
    created_at = getattr(item, "created_at", None)
    return {
        "content_id": item.id,
        "platform": item.platform,
        "source_type": item.source_type or "manual_link",
        "title": item.title,
        "source_url": item.source_url,
        "status": "success",
        "error": None,
        "created_at": created_at.isoformat() if created_at is not None else None,
    }


@collect_routes.post("/extract-from-url")
async def extract_from_url(
    req: ExtractFromUrlRequest,
    _: dict = Depends(verify_token),
):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请输入完整 URL（以 http/https 开头）")

    platform = CollectService.detect_platform(url)
    success, meta = await CollectService.fetch_url_meta(url)

    label = PLATFORM_LABELS.get(platform, "未知平台")
    return {
        "platform": platform,
        "platform_label": label,
        "source_url": url,
        "title": meta.get("title", ""),
        "content_preview": meta.get("description", ""),
        "author_name": meta.get("author", ""),
        "metrics": {},
        "tags": [],
        "comments_preview": [],
        "fetch_success": success,
        "message": "已完成预提取" if success else "已识别平台，但未提取到完整页面信息",
    }


@collect_routes.post("/ingest-page")
def ingest_page(
    req: IngestPageRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=410,
        detail="此接口已停用。内容采集请通过 /api/v1/employee-submissions/link 或 /api/v1/collector/tasks/keyword 提交。",
    )
    # ── 以下代码已失效 ──
    # 优先使用 client_request_id 做幂等去重；若无，则回退为同用户 + 同链接 + 同标题。
    if req.client_request_id:
        dedupe_key = f"[REQ_ID]{req.client_request_id}"
        existing = (
            db.query(ContentAsset)
            .filter(
                ContentAsset.owner_id == current_user["user_id"],
                ContentAsset.manual_note.ilike(f"%{dedupe_key}%"),
            )
            .order_by(ContentAsset.created_at.desc())
            .first()
        )
        if existing:
            return {
                "content_id": existing.id,
                "status": "ingested",
                "dedupe_hit": True,
                "message": "重复提交，已复用已有素材",
            }

    if req.source_url:
        by_url = (
            db.query(ContentAsset)
            .filter(
                ContentAsset.owner_id == current_user["user_id"],
                ContentAsset.source_url == req.source_url,
                ContentAsset.title == req.title,
            )
            .first()
        )
        if by_url:
            return {
                "content_id": by_url.id,
                "status": "ingested",
                "dedupe_hit": True,
                "message": "链接已存在，已复用素材",
            }

    metrics = dict(req.metrics or {})
    if req.comments:
        metrics.setdefault("comment_count", len(req.comments))

    note_lines: list[str] = []
    if req.manual_note:
        note_lines.append(req.manual_note)
    if req.client_request_id:
        note_lines.append(f"[REQ_ID]{req.client_request_id}")
    if req.blocks:
        note_lines.append(f"[BLOCK_COUNT]{len(req.blocks)}")
    if req.snapshot and (req.snapshot.raw_html or req.snapshot.screenshot_url):
        note_lines.append("[HAS_SNAPSHOT]1")

    screenshots: list[str] = []
    if req.snapshot and req.snapshot.screenshot_url:
        screenshots.append(req.snapshot.screenshot_url)

    top_comments = [comment.model_dump() for comment in req.comments[:20]]

    item = ContentAsset(
        owner_id=current_user["user_id"],
        platform=req.platform,
        source_url=req.source_url,
        content_type=req.content_type,
        title=req.title,
        content=req.content_text,
        author=req.author_name,
        publish_time=req.publish_time,
        tags=req.tags,
        top_comments=top_comments,
        comments_keywords=[],
        metrics=metrics,
        source_type=req.source_type,
        category=CollectService.auto_category(req.title, req.content_text),
        manual_note="\n".join(note_lines) if note_lines else None,
        screenshots=screenshots,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    if req.blocks:
        db.add_all(
            [
                ContentBlock(
                    content_id=item.id,
                    block_type=block.block_type,
                    block_order=block.block_order,
                    block_text=block.block_text,
                )
                for block in req.blocks
            ]
        )

    if req.comments:
        db.add_all(
            [
                ContentComment(
                    content_id=item.id,
                    parent_comment_id=comment.parent_comment_id,
                    commenter_name=comment.commenter_name,
                    comment_text=comment.comment_text,
                    like_count=comment.like_count,
                    is_pinned=comment.is_pinned,
                )
                for comment in req.comments
            ]
        )

    if req.snapshot and (req.snapshot.raw_html or req.snapshot.screenshot_url or req.snapshot.page_meta_json):
        db.add(
            ContentSnapshot(
                content_id=item.id,
                raw_html=req.snapshot.raw_html,
                screenshot_url=req.snapshot.screenshot_url,
                page_meta_json=req.snapshot.page_meta_json,
            )
        )

    db.commit()

    return {
        "content_id": item.id,
        "status": "ingested",
        "dedupe_hit": False,
        "message": "已入素材中心",
    }


@collect_routes.post("/ingest-spider-xhs")
def ingest_spider_xhs(
    req: SpiderXHSNoteIn,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    mapped = _build_spider_ingest_request(req)
    return ingest_page(mapped, current_user=current_user, db=db)


@collect_routes.post("/ingest-spider-xhs/batch")
def ingest_spider_xhs_batch(
    req: SpiderXHSBatchIn,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    rows: list[dict[str, Any]] = []
    ok = 0
    dedupe = 0
    failed = 0

    for item in req.items:
        try:
            mapped = _build_spider_ingest_request(item)
            result = ingest_page(mapped, current_user=current_user, db=db)
            dedupe_hit = bool(result.get("dedupe_hit"))
            if dedupe_hit:
                dedupe += 1
            else:
                ok += 1
            rows.append(
                {
                    "note_id": item.note_id,
                    "content_id": result.get("content_id"),
                    "dedupe_hit": dedupe_hit,
                    "status": "ok",
                }
            )
        except Exception as exc:
            failed += 1
            rows.append(
                {
                    "note_id": item.note_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return {
        "total": len(req.items),
        "ok": ok,
        "dedupe": dedupe,
        "failed": failed,
        "rows": rows,
    }


@collect_routes.get("/logs")
def collect_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    source_type: Optional[str] = Query(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    query = db.query(ContentAsset).filter(ContentAsset.owner_id == current_user["user_id"])
    if source_type:
        query = query.filter(ContentAsset.source_type == source_type)

    items = query.order_by(ContentAsset.created_at.desc()).offset(skip).limit(limit).all()
    return [_to_log_row(item) for item in items]


@collect_routes.get("/stats")
def collect_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return CollectService.get_stats(db, current_user["user_id"])


v2_collect_router = APIRouter()
v2_collect_router.include_router(collect_routes)
