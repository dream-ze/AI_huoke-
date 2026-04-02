"""
发布管理 API 端点

负责请求校验和响应返回，业务逻辑委托给 PublishService。
"""

import csv
import io
from datetime import datetime

from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.security import verify_token
from app.models import Customer, Lead, PublishRecord, PublishTask, User
from app.schemas import (
    ContentAnalysisItem,
    PlatformStatsResponse,
    PublishRecordCreate,
    PublishRecordResponse,
    PublishRecordUpdate,
    PublishTaskActionRequest,
    PublishTaskAssignRequest,
    PublishTaskCreate,
    PublishTaskDetailResponse,
    PublishTaskResponse,
    PublishTaskStatsResponse,
    PublishTaskSubmit,
    RoiTrendItem,
)
from app.services.publish_service import PublishService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/publish", tags=["publish"])


# ==================== 发布记录 API ====================


@router.post("/create", response_model=PublishRecordResponse)
def create_publish_record(
    record_data: PublishRecordCreate, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Create publish record."""
    record = PublishService.create_publish_record(db, record_data.model_dump())
    return record


@router.get("/list")
def list_publish_records(
    platform: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List publish records."""
    records = PublishService.list_publish_records(db, platform=platform, skip=skip, limit=limit)
    return records


@router.get("/{record_id}", response_model=PublishRecordResponse)
def get_publish_record(record_id: int, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get specific publish record."""
    record = PublishService.get_publish_record(db, record_id)
    return record


@router.put("/{record_id}", response_model=PublishRecordResponse)
def update_publish_record(
    record_id: int,
    record_data: PublishRecordUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update publish record metrics."""
    update_data = record_data.model_dump(exclude_unset=True)
    record = PublishService.update_publish_record(db, record_id, update_data)
    return record


# ==================== 发布任务 API ====================


@router.post("/tasks/create", response_model=PublishTaskResponse)
def create_publish_task(
    task_data: PublishTaskCreate, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Create publish task for assignment and lifecycle tracking."""
    task = PublishService.create_publish_task(db, task_data.model_dump(), current_user["user_id"])
    return task


@router.get("/tasks/list", response_model=list[PublishTaskResponse])
def list_publish_tasks(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    assigned_to: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List publish tasks that the user created or is assigned to."""
    tasks = PublishService.list_publish_tasks(
        db,
        user_id=current_user["user_id"],
        status_filter=status,
        platform=platform,
        assigned_to=assigned_to,
        skip=skip,
        limit=limit,
    )
    return tasks


@router.get("/tasks/stats", response_model=PublishTaskStatsResponse)
def publish_task_stats(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get task status summary for current user's scope."""
    return PublishService.get_task_stats(db, current_user["user_id"])


@router.get("/tasks/{task_id}", response_model=PublishTaskDetailResponse)
def get_publish_task(task_id: int, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get publish task details."""
    task = PublishService.get_publish_task(db, task_id, current_user["user_id"])
    return task


@router.get("/tasks/{task_id}/trace")
def get_publish_task_trace(task_id: int, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Return trace IDs for publish_task -> lead -> customer link."""
    return PublishService.get_publish_task_trace(db, task_id, current_user["user_id"])


@router.post("/tasks/{task_id}/claim", response_model=PublishTaskResponse)
def claim_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Claim a pending task for execution."""
    task = PublishService.claim_task(db, task_id, current_user["user_id"], req.note)
    return task


@router.post("/tasks/{task_id}/assign", response_model=PublishTaskResponse)
def assign_publish_task(
    task_id: int,
    req: PublishTaskAssignRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Assign or re-assign publish task to a specific user."""
    task = PublishService.assign_task(db, task_id, req.assigned_to, current_user["user_id"], req.note)
    return task


@router.post("/tasks/{task_id}/submit", response_model=PublishTaskResponse)
def submit_publish_task(
    task_id: int, req: PublishTaskSubmit, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Submit publish result and write metrics back."""
    task = PublishService.submit_publish(db, task_id, req.model_dump(), current_user["user_id"])
    return task


@router.post("/tasks/{task_id}/reject", response_model=PublishTaskResponse)
def reject_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Reject task and request rework."""
    task = PublishService.reject_task(db, task_id, current_user["user_id"], req.note)
    return task


@router.post("/tasks/{task_id}/close", response_model=PublishTaskResponse)
def close_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Close task lifecycle after completion or cancellation."""
    task = PublishService.close_task(db, task_id, current_user["user_id"], req.note)
    return task


@router.get("/tasks/export/csv")
def export_publish_tasks_csv(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    current_user: dict = Depends(require_roles("admin", "operator")),
    db: Session = Depends(get_db),
):
    """Export publish tasks in current user scope as CSV."""
    rows = PublishService.export_tasks_csv(
        db,
        user_id=current_user["user_id"],
        status_filter=status,
        platform=platform,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "platform",
            "account_name",
            "task_title",
            "status",
            "assigned_to",
            "post_url",
            "wechat_adds",
            "leads",
            "valid_leads",
            "conversions",
            "created_at",
            "updated_at",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["platform"],
                row["account_name"],
                row["task_title"],
                row["status"],
                row["assigned_to"],
                row["post_url"],
                row["wechat_adds"],
                row["leads"],
                row["valid_leads"],
                row["conversions"],
                row["created_at"],
                row["updated_at"],
            ]
        )

    filename = "publish_tasks_export.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==================== 统计分析 API ====================


@router.get("/stats/by-platform", response_model=list[PlatformStatsResponse])
def get_publish_stats_by_platform(
    days: int = Query(30, ge=1, le=365), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Get platform performance comparison stats."""
    return PublishService.get_platform_stats(db, current_user["user_id"], days)


@router.get("/stats/roi-trend", response_model=list[RoiTrendItem])
def get_publish_roi_trend(
    days: int = Query(30, ge=1, le=365), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Get daily publish-to-conversion ROI trend."""
    return PublishService.get_roi_trend(db, current_user["user_id"], days)


@router.get("/stats/content-analysis", response_model=list[ContentAnalysisItem])
def get_publish_content_analysis(
    days: int = Query(30, ge=1, le=365), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Analyze content performance by platform."""
    return PublishService.get_content_analysis(db, current_user["user_id"], days)


# ==================== 追踪码与线索关联 API ====================


@router.get("/track/{tracking_code}")
def get_content_by_tracking_code(
    tracking_code: str,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """通过追踪码查询发布内容和关联线索."""
    result = PublishService.get_content_with_leads_by_tracking_code(db, tracking_code)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found for this tracking code")
    return result


@router.get("/accounts/{account_id}/leads")
def get_account_lead_stats(
    account_id: int,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """查看账号关联线索统计."""
    date_range = None
    if start_date and end_date:
        date_range = (start_date, end_date)
    return PublishService.get_account_lead_stats(db, account_id, date_range)


@router.get("/contents/{content_id}/leads")
def get_content_lead_stats(
    content_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """查看内容关联线索统计."""
    return PublishService.get_content_lead_stats(db, content_id)
