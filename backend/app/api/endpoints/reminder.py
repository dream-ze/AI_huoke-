from datetime import datetime
from typing import List, Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_token
from app.integrations.wecom.notifier import WeComNotifier
from app.models.models import Customer, ReminderConfig, ReminderLog
from app.tasks.reminder_tasks import get_pending_follow_customers, send_daily_summary_for_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/reminder", tags=["reminder"])


class ReminderConfigUpdate(BaseModel):
    webhook_url: Optional[str] = None
    enabled: bool = True
    daily_summary_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    new_customer_hours: int = Field(default=24, ge=1, le=168)
    high_intent_days: int = Field(default=2, ge=1, le=30)
    normal_days: int = Field(default=7, ge=1, le=90)


class ReminderConfigResponse(BaseModel):
    id: int
    user_id: int
    webhook_url: Optional[str] = None
    enabled: bool
    daily_summary_time: str
    new_customer_hours: int
    high_intent_days: int
    normal_days: int

    class Config:
        from_attributes = True


class PendingCustomerResponse(BaseModel):
    customer_id: int
    nickname: str
    intention_level: str
    days_since_follow: int
    reminder_reason: str


class WebhookTestRequest(BaseModel):
    webhook_url: Optional[str] = None


class WebhookTestResponse(BaseModel):
    success: bool
    message: str


class SendNowResponse(BaseModel):
    success: bool
    message: str
    sent_count: int = 0


@router.get("/config", response_model=ReminderConfigResponse)
def get_reminder_config(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取当前用户的提醒配置"""
    user_id = current_user["user_id"]
    config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()

    if not config:
        # 创建默认配置
        config = ReminderConfig(
            user_id=user_id,
            webhook_url=None,
            enabled=True,
            daily_summary_time="09:00",
            new_customer_hours=24,
            high_intent_days=2,
            normal_days=7,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("/config", response_model=ReminderConfigResponse)
def update_reminder_config(
    config_data: ReminderConfigUpdate, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """更新提醒配置"""
    user_id = current_user["user_id"]
    config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()

    if not config:
        config = ReminderConfig(user_id=user_id)
        db.add(config)

    # 更新字段
    if config_data.webhook_url is not None:
        config.webhook_url = config_data.webhook_url
    config.enabled = config_data.enabled
    config.daily_summary_time = config_data.daily_summary_time
    config.new_customer_hours = config_data.new_customer_hours
    config.high_intent_days = config_data.high_intent_days
    config.normal_days = config_data.normal_days

    db.commit()
    db.refresh(config)
    return config


@router.get("/pending", response_model=List[PendingCustomerResponse])
def get_pending_customers(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取当前待跟进客户列表"""
    user_id = current_user["user_id"]

    # 获取用户配置
    config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()
    if not config:
        config = ReminderConfig(user_id=user_id, new_customer_hours=24, high_intent_days=2, normal_days=7)

    # 获取待跟进客户
    reminders = get_pending_follow_customers(db, user_id, config)

    return [
        PendingCustomerResponse(
            customer_id=r.customer_id,
            nickname=r.nickname,
            intention_level=r.intention_level,
            days_since_follow=r.days_since_follow,
            reminder_reason=r.reminder_reason,
        )
        for r in reminders
    ]


@router.post("/test-webhook", response_model=WebhookTestResponse)
async def test_webhook(
    request: WebhookTestRequest, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """测试 Webhook 连通性"""
    user_id = current_user["user_id"]

    # 确定要测试的 webhook URL
    webhook_url = request.webhook_url
    if not webhook_url:
        config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()
        if config and config.webhook_url:
            webhook_url = config.webhook_url
        else:
            webhook_url = settings.WECOM_WEBHOOK_URL

    if not webhook_url:
        return WebhookTestResponse(success=False, message="未配置 Webhook URL，请在配置中设置或传入 webhook_url 参数")

    try:
        notifier = WeComNotifier(webhook_url)
        content = "## 🔔 连通性测试\n> 这是一条来自智获客系统的测试消息\n\n如果看到这条消息，说明 Webhook 配置正确！"
        result = await notifier.send_markdown(content)

        if result.get("errcode", 0) == 0:
            return WebhookTestResponse(success=True, message="Webhook 测试成功，消息已发送")
        else:
            return WebhookTestResponse(success=False, message=f"Webhook 测试失败: {result.get('errmsg', '未知错误')}")
    except Exception as e:
        return WebhookTestResponse(success=False, message=f"Webhook 测试失败: {str(e)}")


@router.post("/send-now", response_model=SendNowResponse)
async def send_reminder_now(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """手动触发一次提醒"""
    user_id = current_user["user_id"]

    # 获取用户配置
    config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()
    if not config:
        return SendNowResponse(success=False, message="未找到提醒配置，请先配置提醒设置")

    if not config.enabled:
        return SendNowResponse(success=False, message="提醒功能已禁用，请先启用提醒")

    # 检查 webhook 配置
    webhook_url = config.webhook_url or settings.WECOM_WEBHOOK_URL
    if not webhook_url:
        return SendNowResponse(success=False, message="未配置 Webhook URL，无法发送提醒")

    # 获取待跟进客户
    customers = get_pending_follow_customers(db, user_id, config)
    if not customers:
        return SendNowResponse(success=True, message="当前没有需要提醒的待跟进客户", sent_count=0)

    # 发送提醒
    try:
        await send_daily_summary_for_user(user_id)
        return SendNowResponse(
            success=True, message=f"提醒发送成功，共 {len(customers)} 位客户", sent_count=len(customers)
        )
    except Exception as e:
        return SendNowResponse(success=False, message=f"提醒发送失败: {str(e)}", sent_count=0)
