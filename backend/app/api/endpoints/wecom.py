from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.core.permissions import require_roles

router = APIRouter(prefix="/api/wecom", tags=["wecom"])


class WeComNotifyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


@router.post("/notify/test")
async def send_wecom_test_notify(
    payload: WeComNotifyRequest,
    current_user: dict = Depends(require_roles("admin", "operator")),
):
    """Send a test markdown message to WeCom webhook."""
    webhook = (settings.WECOM_WEBHOOK_URL or "").strip()
    if not webhook:
        raise HTTPException(status_code=400, detail="WECOM_WEBHOOK_URL is not configured")

    body = {
        "msgtype": "markdown",
        "markdown": {
            "content": (
                "## 智获客测试通知\n"
                f"> 用户ID: {current_user['user_id']}\n"
                f"> 角色: {current_user['role']}\n"
                f"> 内容: {payload.message}"
            )
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook, json=body)
            resp.raise_for_status()
            result = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WeCom notify failed: {exc}")

    if result.get("errcode") not in (0, "0", None):
        raise HTTPException(status_code=502, detail=f"WeCom API error: {result}")

    return {"ok": True, "result": result}
