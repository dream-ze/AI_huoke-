from datetime import datetime
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.security import verify_token
from app.models import Customer, Lead, PublishRecord, PublishTask, PublishTaskFeedback, RewrittenContent, User
from app.schemas import (
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
)

router = APIRouter(prefix="/api/publish", tags=["publish"])


def _append_task_feedback(
    db: Session,
    task_id: int,
    action: str,
    user_id: int,
    note: str | None = None,
    payload: dict | None = None,
) -> None:
    feedback = PublishTaskFeedback(
        task_id=task_id,
        action=action,
        note=note,
        payload=payload or {},
        created_by=user_id,
    )
    db.add(feedback)


def _get_task_or_404(db: Session, task_id: int) -> PublishTask:
    task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish task not found")
    return task


def _check_task_access(task: PublishTask, user_id: int) -> None:
    if task.owner_id != user_id and task.assigned_to != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this publish task")


def _derive_lead_status(task: PublishTask) -> str:
    if (task.conversions or 0) > 0:
        return "converted"
    if (task.valid_leads or 0) > 0:
        return "qualified"
    if (task.leads or 0) > 0 or (task.wechat_adds or 0) > 0:
        return "contacted"
    return "new"


def _upsert_lead_from_task(db: Session, task: PublishTask) -> Lead:
    lead = db.query(Lead).filter(Lead.publish_task_id == task.id).first()
    owner_id = task.assigned_to or task.owner_id
    lead_status = _derive_lead_status(task)

    if lead is None:
        lead = Lead(
            owner_id=owner_id,
            publish_task_id=task.id,
            platform=task.platform,
            source="publish_task",
            title=task.task_title,
            post_url=task.post_url,
            wechat_adds=task.wechat_adds or 0,
            leads=task.leads or 0,
            valid_leads=task.valid_leads or 0,
            conversions=task.conversions or 0,
            status=lead_status,
            intention_level="medium",
            note="自动由发布任务回填生成/归并",
        )
        db.add(lead)
        db.flush()
    else:
        lead.owner_id = owner_id
        lead.platform = task.platform
        lead.title = task.task_title
        lead.post_url = task.post_url
        lead.wechat_adds = task.wechat_adds or 0
        lead.leads = task.leads or 0
        lead.valid_leads = task.valid_leads or 0
        lead.conversions = task.conversions or 0
        lead.status = lead_status

    customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
    if customer:
        customer.owner_id = lead.owner_id
        customer.customer_status = "converted" if lead.status == "converted" else customer.customer_status
    elif lead.conversions > 0:
        customer = Customer(
            owner_id=lead.owner_id,
            nickname=f"线索#{lead.id}",
            source_platform=lead.platform,
            source_content_id=task.rewritten_content_id,
            lead_id=lead.id,
            customer_status="converted",
            tags=["自动转客户", "来自发布任务"],
            intention_level="high",
            inquiry_content=f"由发布任务#{task.id}自动转化",
        )
        db.add(customer)

    return lead


@router.post("/create", response_model=PublishRecordResponse)
def create_publish_record(
    record_data: PublishRecordCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create publish record."""
    rewritten = db.query(RewrittenContent).filter(
        RewrittenContent.id == record_data.rewritten_content_id
    ).first()

    if not rewritten:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rewritten content not found"
        )

    publish_record = PublishRecord(**record_data.model_dump())
    db.add(publish_record)
    db.commit()
    db.refresh(publish_record)
    return publish_record


@router.post("/tasks/create", response_model=PublishTaskResponse)
def create_publish_task(
    task_data: PublishTaskCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create publish task for assignment and lifecycle tracking."""
    if task_data.rewritten_content_id is not None:
        rewritten = (
            db.query(RewrittenContent)
            .filter(RewrittenContent.id == task_data.rewritten_content_id)
            .first()
        )
        if not rewritten:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rewritten content not found",
            )

    task = PublishTask(
        owner_id=current_user["user_id"],
        **task_data.model_dump(),
    )
    db.add(task)
    db.flush()
    _append_task_feedback(
        db,
        task_id=task.id,
        action="create",
        user_id=current_user["user_id"],
        note="任务已创建",
    )
    db.commit()
    db.refresh(task)
    return task


@router.get("/list")
def list_publish_records(
    platform: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """List publish records."""
    query = db.query(PublishRecord)

    if platform:
        query = query.filter(PublishRecord.platform == platform)

    records = query.order_by(PublishRecord.publish_time.desc())\
        .offset(skip).limit(limit).all()
    return records


@router.get("/tasks/list", response_model=list[PublishTaskResponse])
def list_publish_tasks(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    assigned_to: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """List publish tasks that the user created or is assigned to."""
    query = db.query(PublishTask).filter(
        or_(
            PublishTask.owner_id == current_user["user_id"],
            PublishTask.assigned_to == current_user["user_id"],
        )
    )

    if status and status != "all":
        query = query.filter(PublishTask.status == status)
    if platform and platform != "all":
        query = query.filter(PublishTask.platform == platform)
    if assigned_to is not None:
        query = query.filter(PublishTask.assigned_to == assigned_to)

    return query.order_by(PublishTask.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/tasks/stats", response_model=PublishTaskStatsResponse)
def publish_task_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get task status summary for current user's scope."""
    rows = (
        db.query(PublishTask.status, func.count(PublishTask.id))
        .filter(
            or_(
                PublishTask.owner_id == current_user["user_id"],
                PublishTask.assigned_to == current_user["user_id"],
            )
        )
        .group_by(PublishTask.status)
        .all()
    )
    status_map = {key: count for key, count in rows if key}
    total = sum(status_map.values())
    return {
        "total": total,
        "pending": status_map.get("pending", 0),
        "claimed": status_map.get("claimed", 0),
        "submitted": status_map.get("submitted", 0),
        "rejected": status_map.get("rejected", 0),
        "closed": status_map.get("closed", 0),
    }


@router.get("/{record_id}", response_model=PublishRecordResponse)
def get_publish_record(
    record_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get specific publish record."""
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publish record not found"
        )

    return record


@router.get("/tasks/{task_id}", response_model=PublishTaskDetailResponse)
def get_publish_task(
    task_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])
    return task


@router.get("/tasks/{task_id}/trace")
def get_publish_task_trace(
    task_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Return trace IDs for publish_task -> lead -> customer link."""
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])

    lead = db.query(Lead).filter(Lead.publish_task_id == task.id).first()
    customer = db.query(Customer).filter(Customer.lead_id == lead.id).first() if lead else None

    return {
        "task_id": task.id,
        "publish_record_id": task.publish_record_id,
        "lead_id": lead.id if lead else None,
        "customer_id": customer.id if customer else None,
    }


@router.put("/{record_id}", response_model=PublishRecordResponse)
def update_publish_record(
    record_id: int,
    record_data: PublishRecordUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update publish record metrics."""
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publish record not found"
        )

    update_data = record_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.post("/tasks/{task_id}/claim", response_model=PublishTaskResponse)
def claim_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Claim a pending task for execution."""
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])

    if task.status not in {"pending", "rejected"}:
        raise HTTPException(status_code=400, detail="Only pending/rejected tasks can be claimed")

    if task.assigned_to and task.assigned_to != current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Task is assigned to another user")

    task.assigned_to = current_user["user_id"]
    task.status = "claimed"
    task.claimed_at = datetime.utcnow()

    _append_task_feedback(
        db,
        task_id=task.id,
        action="claim",
        user_id=current_user["user_id"],
        note=req.note,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/assign", response_model=PublishTaskResponse)
def assign_publish_task(
    task_id: int,
    req: PublishTaskAssignRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Assign or re-assign publish task to a specific user."""
    task = _get_task_or_404(db, task_id)

    if task.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only task owner can assign task")

    if task.status in {"submitted", "closed"}:
        raise HTTPException(status_code=400, detail="Submitted/closed task cannot be re-assigned")

    assignee = db.query(User).filter(User.id == req.assigned_to, User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee user not found or inactive")

    task.assigned_to = req.assigned_to
    task.status = "pending"
    task.claimed_at = None

    _append_task_feedback(
        db,
        task_id=task.id,
        action="assign",
        user_id=current_user["user_id"],
        note=req.note,
        payload={"assigned_to": req.assigned_to},
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/submit", response_model=PublishTaskResponse)
def submit_publish_task(
    task_id: int,
    req: PublishTaskSubmit,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Submit publish result and write metrics back."""
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])

    if task.status in {"closed", "rejected"}:
        raise HTTPException(status_code=400, detail="Closed/rejected task cannot be submitted")

    if task.assigned_to and task.assigned_to != current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Only assignee can submit this task")

    if task.assigned_to is None:
        task.assigned_to = current_user["user_id"]
        task.claimed_at = datetime.utcnow()

    updates = req.model_dump(exclude_unset=True)
    note = updates.pop("note", None)
    for field, value in updates.items():
        setattr(task, field, value)

    task.posted_at = req.posted_at or datetime.utcnow()
    task.status = "submitted"

    if task.rewritten_content_id:
        if task.publish_record_id:
            record = db.query(PublishRecord).filter(PublishRecord.id == task.publish_record_id).first()
        else:
            record = PublishRecord(
                rewritten_content_id=task.rewritten_content_id,
                platform=task.platform,
                account_name=task.account_name,
                publish_time=task.posted_at,
                published_by=str(current_user["user_id"]),
            )
            db.add(record)
            db.flush()
            task.publish_record_id = record.id

        if record:
            for field in (
                "views",
                "likes",
                "comments",
                "favorites",
                "shares",
                "private_messages",
                "wechat_adds",
                "leads",
                "valid_leads",
                "conversions",
            ):
                setattr(record, field, getattr(task, field))
            record.publish_time = task.posted_at
            record.published_by = str(current_user["user_id"])

    _append_task_feedback(
        db,
        task_id=task.id,
        action="submit",
        user_id=current_user["user_id"],
        note=note,
        payload=updates,
    )

    _upsert_lead_from_task(db, task)

    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/reject", response_model=PublishTaskResponse)
def reject_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Reject task and request rework."""
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])

    if task.status == "closed":
        raise HTTPException(status_code=400, detail="Closed task cannot be rejected")

    task.status = "rejected"
    task.reject_reason = req.note

    _append_task_feedback(
        db,
        task_id=task.id,
        action="reject",
        user_id=current_user["user_id"],
        note=req.note,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/close", response_model=PublishTaskResponse)
def close_publish_task(
    task_id: int,
    req: PublishTaskActionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Close task lifecycle after completion or cancellation."""
    task = _get_task_or_404(db, task_id)
    _check_task_access(task, current_user["user_id"])

    if task.status == "closed":
        return task

    task.status = "closed"
    task.close_reason = req.note
    task.closed_at = datetime.utcnow()

    _append_task_feedback(
        db,
        task_id=task.id,
        action="close",
        user_id=current_user["user_id"],
        note=req.note,
    )
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/export/csv")
def export_publish_tasks_csv(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    current_user: dict = Depends(require_roles("admin", "operator")),
    db: Session = Depends(get_db),
):
    """Export publish tasks in current user scope as CSV."""
    query = db.query(PublishTask).filter(
        or_(
            PublishTask.owner_id == current_user["user_id"],
            PublishTask.assigned_to == current_user["user_id"],
        )
    )

    if status and status != "all":
        query = query.filter(PublishTask.status == status)
    if platform and platform != "all":
        query = query.filter(PublishTask.platform == platform)

    tasks = query.order_by(PublishTask.created_at.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
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
    ])

    for item in tasks:
        writer.writerow([
            item.id,
            item.platform,
            item.account_name,
            item.task_title,
            item.status,
            item.assigned_to or "",
            item.post_url or "",
            item.wechat_adds or 0,
            item.leads or 0,
            item.valid_leads or 0,
            item.conversions or 0,
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        ])

    filename = "publish_tasks_export.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
