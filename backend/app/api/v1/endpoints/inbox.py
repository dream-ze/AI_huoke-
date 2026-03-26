from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import MaterialInbox
from app.services.collector import AcquisitionIntakeService

v1_inbox_router = APIRouter(prefix="/material", tags=["material-inbox-v1"])


# ─────────────────────────────────────────
# 请求 / 响应 Schema
# ─────────────────────────────────────────

class ApproveRequest(BaseModel):
    remark: Optional[str] = None


class ManualInboxRequest(BaseModel):
    platform: str
    title: str
    content: str
    tags: list[str] = []
    note: Optional[str] = None


class ToTopicRequest(BaseModel):
    topic_id: int
    remark: Optional[str] = None


class NegativeCaseRequest(BaseModel):
    remark: Optional[str] = None


class DiscardRequest(BaseModel):
    remark: Optional[str] = None


# ─────────────────────────────────────────
# 工具
# ─────────────────────────────────────────

def _to_row(item: MaterialInbox) -> dict[str, Any]:
    created_at = getattr(item, "created_at", None)
    updated_at = getattr(item, "updated_at", None)
    publish_time = getattr(item, "publish_time", None)
    return {
        "id": item.id,
        "source_channel": item.source_channel,
        "source_task_id": item.source_task_id,
        "source_submission_id": item.source_submission_id,
        "platform": item.platform,
        "title": item.title,
        "author": item.author,
        "content": item.content,
        "url": item.url,
        "cover_url": item.cover_url,
        "like_count": item.like_count,
        "comment_count": item.comment_count,
        "collect_count": item.collect_count,
        "share_count": item.share_count,
        "publish_time": publish_time.isoformat() if publish_time else None,
        "raw_data": item.raw_data or {},
        "status": item.status,
        "submitted_by_employee_id": item.submitted_by_employee_id,
        "remark": item.remark,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


# ─────────────────────────────────────────
# 列表查询（静态路由必须在动态路由之前）
# ─────────────────────────────────────────

@v1_inbox_router.get(
    "/inbox",
    summary="收件箱列表",
    description="查询当前用户的收件箱条目，支持按 status / platform / source_channel 过滤。",
)
def list_material_inbox(
    status: Optional[str] = Query(default=None, description="pending / approved / negative_case / discarded"),
    platform: Optional[str] = Query(default=None),
    source_channel: Optional[str] = Query(default=None, description="collect_task / employee_submission / wechat_robot"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    items = AcquisitionIntakeService.list_inbox(
        db=db,
        owner_id=current_user["user_id"],
        status=status,
        platform=platform,
        source_channel=source_channel,
        skip=skip,
        limit=limit,
    )
    return [_to_row(item) for item in items]


@v1_inbox_router.post(
    "/inbox/manual",
    summary="手动录入内容到收件箱",
    description="将手动填写的标题/正文直接提交到收件箱，状态为 pending，等待人工审核。",
)
def submit_manual_to_inbox(
    req: ManualInboxRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return AcquisitionIntakeService.submit_manual(
        db=db,
        owner_id=current_user["user_id"],
        platform=req.platform,
        title=req.title,
        content=req.content,
        tags=req.tags,
        note=req.note,
    )


# ─────────────────────────────────────────
# 分拣动作（POST /inbox/{id}/动作）
# 必须注册在 GET /inbox/{inbox_id} 之前，
# 以防动态路由抢先匹配。
# ─────────────────────────────────────────

@v1_inbox_router.post(
    "/inbox/{inbox_id}/approve",
    summary="审核通过 – 入素材库与洞察库",
    description=(
        "将 pending 状态的收件箱条目提升到 ContentAsset（素材库）和 InsightContentItem（洞察库）。"
        "操作幂等保护：非 pending 状态的条目返回 409。"
    ),
)
def approve_inbox_item(
    inbox_id: int,
    req: ApproveRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.approve_item(db, current_user["user_id"], inbox_id, req.remark)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@v1_inbox_router.post(
    "/inbox/{inbox_id}/to-topic",
    summary="挂主题 – 入洞察库并关联指定主题",
    description=(
        "将 pending 收件箱条目提升到 ContentAsset 和 InsightContentItem，并绑定 topic_id 对应的主题。"
        "若 topic_id 不存在返回 404；非 pending 状态返回 409。"
    ),
)
def to_topic_inbox_item(
    inbox_id: int,
    req: ToTopicRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.to_topic_item(
            db, current_user["user_id"], inbox_id, req.topic_id, req.remark
        )
    except ValueError as exc:
        status_code = 404 if "不存在" in str(exc) and "主题" in str(exc) else 409
        raise HTTPException(status_code=status_code, detail=str(exc))


@v1_inbox_router.post(
    "/inbox/{inbox_id}/to-negative-case",
    summary="标记为反案例 – 入洞察库",
    description=(
        "将 pending 收件箱条目标记为反案例并写入 InsightContentItem（manual_note 前缀 [反案例]），"
        "不创建 ContentAsset。非 pending 状态返回 409。"
    ),
)
def to_negative_case_inbox_item(
    inbox_id: int,
    req: NegativeCaseRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.to_negative_case_item(
            db, current_user["user_id"], inbox_id, req.remark
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@v1_inbox_router.post(
    "/inbox/{inbox_id}/discard",
    summary="丢弃收件箱条目",
    description="将 pending 条目状态置为 discarded，不创建任何下游记录。非 pending 状态返回 409。",
)
def discard_inbox_item(
    inbox_id: int,
    req: DiscardRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.discard_item(db, current_user["user_id"], inbox_id, req.remark)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ─────────────────────────────────────────
# 单条详情（动态路由放最后）
# ─────────────────────────────────────────

@v1_inbox_router.get(
    "/inbox/{inbox_id}",
    summary="收件箱条目详情",
)
def get_material_inbox_detail(
    inbox_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = AcquisitionIntakeService.get_inbox_item(db, current_user["user_id"], inbox_id)
    if item is None:
        raise HTTPException(status_code=404, detail="收件箱内容不存在")
    return _to_row(item)

