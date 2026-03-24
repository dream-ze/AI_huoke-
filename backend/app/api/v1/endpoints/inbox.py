from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.acquisition.inbox_service import InboxService
from app.domains.ai_workbench.ai_service import AIService
from app.schemas import (
    InboxAutoMergeRequest,
    InboxBatchActionResponse,
    InboxBatchAssignRequest,
    InboxBatchDiscardRequest,
    InboxBatchPromoteRequest,
    InboxCreateRequest,
    InboxDedupePreviewResponse,
    InboxPromoteResponse,
    InboxResponse,
    InboxStatsResponse,
    InboxUpdateRequest,
)

inbox_routes = APIRouter(tags=["inbox"])


@inbox_routes.post("/create", response_model=InboxResponse)
def create_inbox_item(
    req: InboxCreateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.create_item(db, current_user["user_id"], req.model_dump())


@inbox_routes.get("/list", response_model=list[InboxResponse])
def list_inbox_items(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.list_items(db, current_user["user_id"], status, platform, search, skip, limit)


@inbox_routes.get("/stats", response_model=InboxStatsResponse)
def inbox_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.get_stats(db, current_user["user_id"])


@inbox_routes.post("/batch-actions/assign", response_model=InboxBatchActionResponse)
def batch_assign_inbox_items(
    req: InboxBatchAssignRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.batch_assign(
        db,
        user_id=current_user["user_id"],
        inbox_ids=req.inbox_ids,
        assignee_user_id=req.assignee_user_id,
        note_template=req.note_template,
    )


@inbox_routes.post("/batch-actions/discard", response_model=InboxBatchActionResponse)
def batch_discard_inbox_items(
    req: InboxBatchDiscardRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.batch_discard(
        db,
        user_id=current_user["user_id"],
        inbox_ids=req.inbox_ids,
        review_note=req.review_note,
    )


@inbox_routes.post("/batch-actions/promote", response_model=InboxBatchActionResponse)
def batch_promote_inbox_items(
    req: InboxBatchPromoteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.batch_promote(
        db,
        user_id=current_user["user_id"],
        inbox_ids=req.inbox_ids,
    )


@inbox_routes.post("/dedupe/auto-merge", response_model=InboxBatchActionResponse)
def dedupe_auto_merge(
    req: InboxAutoMergeRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.auto_merge_duplicates(
        db,
        user_id=current_user["user_id"],
        keep_strategy=req.keep_strategy,
        dry_run=req.dry_run,
    )


@inbox_routes.get("/dedupe/preview", response_model=InboxDedupePreviewResponse)
def dedupe_preview(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InboxService.dedupe_preview(db, user_id=current_user["user_id"])


@inbox_routes.put("/{inbox_id}", response_model=InboxResponse)
def update_inbox_item(
    inbox_id: int,
    req: InboxUpdateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = InboxService.get_item(db, current_user["user_id"], inbox_id)
    return InboxService.update_item(db, item, req.model_dump(exclude_unset=True))


@inbox_routes.post("/{inbox_id}/analyze", response_model=InboxResponse)
async def analyze_inbox_item(
    inbox_id: int,
    force_cloud: bool = Query(False, description="强制使用云端模型"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = InboxService.get_item(db, current_user["user_id"], inbox_id)
    ai_service = AIService(db=db)
    return await InboxService.analyze_item(db, item, ai_service, force_cloud, current_user["user_id"])


@inbox_routes.post("/{inbox_id}/promote", response_model=InboxPromoteResponse)
def promote_inbox_item(
    inbox_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = InboxService.get_item(db, current_user["user_id"], inbox_id)
    return InboxService.promote_item(db, item)


@inbox_routes.post("/{inbox_id}/discard", response_model=InboxResponse)
def discard_inbox_item(
    inbox_id: int,
    review_note: Optional[str] = Query(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = InboxService.get_item(db, current_user["user_id"], inbox_id)
    return InboxService.discard_item(db, item, review_note)


v1_inbox_router = APIRouter(prefix="/inbox")
v1_inbox_router.include_router(inbox_routes)