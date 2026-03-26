import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.services.collector import AcquisitionIntakeService

v1_submissions_router = APIRouter(prefix="/employee-submissions", tags=["employee-submissions-v1"])
v1_integrations_router = APIRouter(prefix="/integrations", tags=["integrations-v1"])


class EmployeeLinkSubmissionRequest(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    note: str | None = Field(default=None, max_length=500)


class WechatCallbackRequest(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    message: str = Field(min_length=1, max_length=5000)
    note: str | None = Field(default=None, max_length=500)


def _extract_urls(message: str) -> list[str]:
    pattern = re.compile(r"https?://[^\s]+", re.IGNORECASE)
    return [url.strip() for url in pattern.findall(message)]


@v1_submissions_router.post("/link")
def submit_employee_link(
    req: EmployeeLinkSubmissionRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    try:
        result = AcquisitionIntakeService.submit_link(
            db=db,
            owner_id=current_user["user_id"],
            employee_id=current_user["user_id"],
            url=req.url,
            note=req.note,
            source_type="manual_link",
        )
        return {"submission_id": result["submission_id"], "status": result["status"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"链接采集失败: {exc}") from exc


@v1_integrations_router.post("/wechat/callback")
def wechat_callback(
    req: WechatCallbackRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    urls = _extract_urls(req.message)
    if not urls:
        raise HTTPException(status_code=400, detail="消息中未找到可采集链接")

    rows: list[dict] = []
    ok = 0
    failed = 0
    target_employee_id = req.employee_id or current_user["user_id"]

    for url in urls:
        try:
            result = AcquisitionIntakeService.submit_link(
                db=db,
                owner_id=current_user["user_id"],
                employee_id=target_employee_id,
                url=url,
                note=req.note,
                source_type="wechat_robot",
            )
            rows.append({"url": url, "submission_id": result["submission_id"], "status": "success"})
            ok += 1
        except Exception as exc:
            rows.append({"url": url, "status": "failed", "error": str(exc)})
            failed += 1

    return {
        "total": len(urls),
        "ok": ok,
        "failed": failed,
        "rows": rows,
    }
