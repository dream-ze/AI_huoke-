from datetime import datetime
from typing import Any, Optional

from app.collector.metrics import CollectMetricsQuery, get_recent_stats
from app.collector.services.collect_service import PLATFORM_LABELS, CollectService
from app.core.database import get_db
from app.core.security import verify_token
from app.models import CollectTask, MaterialItem
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session


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


def _to_log_row(item: MaterialItem) -> dict[str, Any]:
    created_at = getattr(item, "created_at", None)
    return {
        "material_id": item.id,
        "platform": item.platform,
        "source_channel": item.source_channel,
        "title": item.title,
        "source_url": item.source_url,
        "status": item.status,
        "risk_status": item.risk_status,
        "filter_reason": item.filter_reason,
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
    _ = req
    _ = current_user
    _ = db
    raise HTTPException(
        status_code=410,
        detail="此接口已停用。内容采集请通过 /api/v1/employee-submissions/link 或 /api/v1/collector/tasks/keyword 提交。",
    )


@collect_routes.post("/ingest-spider-xhs")
def ingest_spider_xhs(
    req: SpiderXHSNoteIn,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    _ = req
    _ = current_user
    _ = db
    raise HTTPException(
        status_code=410,
        detail="Spider_XHS 旧直写接口已停用，请改为先落地新素材管道或使用历史回填脚本。",
    )


@collect_routes.post("/ingest-spider-xhs/batch")
def ingest_spider_xhs_batch(
    req: SpiderXHSBatchIn,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    _ = req
    _ = current_user
    _ = db
    raise HTTPException(
        status_code=410,
        detail="Spider_XHS 批量直写接口已停用，请使用 scripts/backfill_material_pipeline.py 或新的采集入口。",
    )


@collect_routes.get("/logs")
def collect_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    source_type: Optional[str] = Query(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    query = db.query(MaterialItem).filter(MaterialItem.owner_id == current_user["user_id"])
    if source_type:
        source_channel = {
            "manual_link": "employee_submission",
            "wechat_robot": "wechat_robot",
            "keyword": "collect_task",
            "manual_input": "manual_input",
        }.get(source_type, source_type)
        query = query.filter(MaterialItem.source_channel == source_channel)

    items = query.order_by(MaterialItem.created_at.desc()).offset(skip).limit(limit).all()
    return [_to_log_row(item) for item in items]


@collect_routes.get("/stats")
def collect_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90, description="查询天数范围（1-90天）"),
    platform: Optional[str] = Query(None, description="按平台筛选"),
):
    """
    获取采集统计信息。

    返回近期采集任务的统计数据，包括：
    - 成功率、失败率
    - 按平台分布
    - 去重统计
    - 平均耗时
    """
    owner_id = current_user["user_id"]

    # 1. 素材库整体统计
    total_materials = db.query(func.count(MaterialItem.id)).filter(MaterialItem.owner_id == owner_id).scalar() or 0
    by_platform_rows = (
        db.query(MaterialItem.platform, func.count(MaterialItem.id))
        .filter(MaterialItem.owner_id == owner_id)
        .group_by(MaterialItem.platform)
        .all()
    )
    by_status_rows = (
        db.query(MaterialItem.status, func.count(MaterialItem.id))
        .filter(MaterialItem.owner_id == owner_id)
        .group_by(MaterialItem.status)
        .all()
    )
    duplicate_count = (
        db.query(func.count(MaterialItem.id))
        .filter(MaterialItem.owner_id == owner_id, MaterialItem.is_duplicate.is_(True))
        .scalar()
        or 0
    )

    # 2. 近期采集任务统计（使用 metrics 模块）
    recent_stats = get_recent_stats(db, owner_id, days=days, platform=platform)

    # 3. 近期任务明细（最近10条）
    recent_tasks = (
        db.query(CollectTask)
        .filter(CollectTask.owner_id == owner_id)
        .order_by(CollectTask.created_at.desc())
        .limit(10)
        .all()
    )

    task_list = []
    for task in recent_tasks:
        task_list.append(
            {
                "task_id": task.id,
                "platform": task.platform,
                "keyword": task.keyword,
                "status": task.status,
                "result_count": task.result_count or 0,
                "inserted_count": task.inserted_count or 0,
                "failed_count": task.failed_count or 0,
                "duplicate_count": task.duplicate_count or 0,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": (
                    task.completed_at.isoformat() if hasattr(task, "completed_at") and task.completed_at else None
                ),
            }
        )

    return {
        "summary": {
            "total_materials": int(total_materials),
            "duplicate_count": int(duplicate_count),
            "by_platform": {platform: count for platform, count in by_platform_rows if platform},
            "by_status": {status: count for status, count in by_status_rows if status},
        },
        "recent_period": {"days": days, "platform_filter": platform, **recent_stats},
        "recent_tasks": task_list,
    }


@collect_routes.get("/stats/overview")
def collect_stats_overview(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    获取采集系统整体概览统计。

    适用于仪表盘展示。
    """
    owner_id = current_user["user_id"]

    overall = CollectMetricsQuery.get_overall_stats(db, owner_id)

    # 今日统计
    from datetime import timedelta

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    today_tasks = (
        db.query(CollectTask).filter(CollectTask.owner_id == owner_id, CollectTask.created_at >= today_start).all()
    )

    today_stats = {
        "tasks_count": len(today_tasks),
        "inserted": sum(t.inserted_count or 0 for t in today_tasks),
        "failed": sum(t.failed_count or 0 for t in today_tasks),
        "duplicate": sum(t.duplicate_count or 0 for t in today_tasks),
    }

    return {"overall": overall, "today": today_stats}


v2_collect_router = APIRouter()
v2_collect_router.include_router(collect_routes)
