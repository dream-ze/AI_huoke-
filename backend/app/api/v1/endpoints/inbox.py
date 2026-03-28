from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.acquisition import MaterialPipelineOrchestrator
from app.domains.ai_workbench.ai_service import AIService
from app.services.collector import AcquisitionIntakeService

v1_inbox_router = APIRouter(prefix="/material", tags=["material-inbox-v1"])


class ManualInboxRequest(BaseModel):
    platform: str
    title: str
    content: str
    tags: list[str] = []
    note: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str
    review_note: Optional[str] = None


class RewriteRequest(BaseModel):
    platform: str = Field(default="xiaohongshu", min_length=2, max_length=50)
    account_type: str = Field(default="科普号", min_length=2, max_length=50)
    target_audience: str = Field(default="泛人群", min_length=2, max_length=50)
    task_type: str = Field(default="rewrite", min_length=2, max_length=50)


def _to_row(item: Any) -> dict[str, Any]:
    return AcquisitionIntakeService.serialize_material_item(item)


@v1_inbox_router.get(
    "/inbox",
    summary="收件箱列表",
    description="查询当前用户收件箱，支持按三段式状态和过滤字段检索。",
)
def list_material_inbox(
    status: Optional[str] = Query(default=None, description="pending / review / discard"),
    platform: Optional[str] = Query(default=None),
    source_channel: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    risk_status: Optional[str] = Query(default=None),
    is_duplicate: Optional[bool] = Query(default=None),
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
        keyword=keyword,
        risk_status=risk_status,
        is_duplicate=is_duplicate,
        skip=skip,
        limit=limit,
        include_source_content=True,
    )
    return [_to_row(item) for item in items]


@v1_inbox_router.post(
    "/inbox/manual",
    summary="手动录入到收件箱",
    description="手动内容录入统一进入 review 状态，等待人工处理。",
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


@v1_inbox_router.patch(
    "/inbox/{inbox_id}/status",
    summary="更新收件箱状态",
    description="按状态机更新 pending/review/discard。",
)
def update_material_inbox_status(
    inbox_id: int,
    req: UpdateStatusRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.update_inbox_status(
            db=db,
            owner_id=current_user["user_id"],
            inbox_id=inbox_id,
            target_status=req.status,
            review_note=req.review_note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "不存在" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)


@v1_inbox_router.get(
    "/inbox/{inbox_id}",
    summary="收件箱条目详情",
)
def get_material_inbox_detail(
    inbox_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = AcquisitionIntakeService.get_inbox_item(
        db=db,
        owner_id=current_user["user_id"],
        inbox_id=inbox_id,
        include_source_content=True,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="收件箱内容不存在")
    return _to_row(item)


@v1_inbox_router.post(
    "/inbox/{inbox_id}/rewrite",
    summary="基于收件箱素材生成文案",
    description="收件箱只是素材视图，改写直接基于 material_items + knowledge_documents 检索生成。",
)
async def rewrite_material_from_inbox(
    inbox_id: int,
    req: RewriteRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        orchestrator = MaterialPipelineOrchestrator(
            db=db,
            owner_id=current_user["user_id"],
            ai_service=AIService(db=db),
        )
        return await orchestrator.generate_from_material(
            material_id=inbox_id,
            platform=req.platform,
            account_type=req.account_type,
            target_audience=req.target_audience,
            task_type=req.task_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
