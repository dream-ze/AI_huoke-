from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.collector.services.pipeline import AcquisitionIntakeService

v1_collect_router = APIRouter(prefix="/collector", tags=["collector-v1"])


class KeywordTaskCreateRequest(BaseModel):
    platform: str = Field(min_length=2, max_length=30)
    keyword: str = Field(min_length=1, max_length=255)
    max_items: int = Field(default=20, ge=1, le=100)


@v1_collect_router.post("/tasks/keyword")
def create_keyword_task(
    req: KeywordTaskCreateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        return AcquisitionIntakeService.create_keyword_task(
            db=db,
            owner_id=current_user["user_id"],
            platform=req.platform,
            keyword=req.keyword,
            max_items=req.max_items,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"调用采集服务失败: {exc}") from exc
