"""提醒任务 - 企业微信跟进提醒"""

import logging
from datetime import datetime, timedelta
from typing import List

from app.celery_app import celery
from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.wecom.notifier import CustomerReminder, WeComNotifier
from app.models.models import Customer, ReminderConfig, ReminderLog, User
from celery import shared_task
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_pending_follow_customers(db: Session, user_id: int, config: ReminderConfig) -> List[CustomerReminder]:
    """查询需要提醒的待跟进客户"""
    now = datetime.utcnow()
    results = []

    customers = (
        db.query(Customer)
        .filter(Customer.owner_id == user_id, Customer.customer_status.in_(["new", "pending_follow", "contacted"]))
        .all()
    )

    for c in customers:
        reminder_reason = None
        days_since_follow = 0

        if c.last_follow_at:
            days_since_follow = (now - c.last_follow_at).days
        else:
            days_since_follow = (now - c.created_at).days

        # 判断提醒条件
        if c.next_follow_at and c.next_follow_at <= now:
            reminder_reason = "scheduled"
        elif c.customer_status == "new" and not c.last_follow_at:
            hours_since_create = (now - c.created_at).total_seconds() / 3600
            if hours_since_create >= config.new_customer_hours:
                reminder_reason = "new_customer"
        elif c.intention_level == "high" and days_since_follow >= config.high_intent_days:
            reminder_reason = "high_intent_overdue"
        elif days_since_follow >= config.normal_days:
            reminder_reason = "normal_overdue"

        if reminder_reason:
            # 检查24小时内是否已发过提醒
            recent_log = (
                db.query(ReminderLog)
                .filter(ReminderLog.customer_id == c.id, ReminderLog.created_at >= now - timedelta(hours=24))
                .first()
            )

            if not recent_log:
                results.append(
                    CustomerReminder(
                        customer_id=c.id,
                        nickname=c.nickname,
                        intention_level=c.intention_level or "medium",
                        last_follow_at=c.last_follow_at,
                        days_since_follow=days_since_follow,
                        reminder_reason=reminder_reason,
                    )
                )

    return results


def _send_daily_summary_for_user(user_id: int) -> dict:
    """为单个用户发送每日汇总 (同步版本)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "reason": "user_not_found"}

        config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()

        if not config or not config.enabled:
            return {"status": "skipped", "reason": "config_disabled"}

        customers = get_pending_follow_customers(db, user_id, config)
        if not customers:
            logger.info(f"User {user_id} has no pending customers")
            return {"status": "skipped", "reason": "no_customers"}

        webhook_url = config.webhook_url or settings.WECOM_WEBHOOK_URL
        if not webhook_url:
            logger.warning(f"User {user_id} has no webhook configured")
            return {"status": "error", "reason": "no_webhook"}

        notifier = WeComNotifier(webhook_url)
        result = notifier.send_daily_summary_sync(
            user_name=user.username, customers=customers, frontend_url=settings.FRONTEND_URL
        )

        # 记录日志
        for c in customers:
            log = ReminderLog(
                user_id=user_id,
                customer_id=c.customer_id,
                reminder_type="daily_summary",
                channel="wecom",
                status="sent" if result.get("errcode", 0) == 0 else "failed",
                message_preview=f"每日汇总：{c.nickname}",
            )
            db.add(log)

        db.commit()
        logger.info(f"Sent daily summary to user {user_id}, {len(customers)} customers")
        return {"status": "success", "customers_count": len(customers)}

    except Exception as e:
        logger.exception(f"Failed to send daily summary for user {user_id}: {e}")
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


async def send_daily_summary_for_user(user_id: int) -> dict:
    """供 API 路由调用的异步包装器。"""
    return _send_daily_summary_for_user(user_id)


@shared_task(bind=True, max_retries=3)
def run_reminder_tasks(self) -> None:
    """定时任务入口（每小时检查紧急提醒）"""
    try:
        _check_urgent_reminders()
    except Exception as exc:
        logger.error(f"run_reminder_tasks failed: {exc}, retrying...")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def run_daily_summary_tasks(self) -> None:
    """每日汇总任务入口"""
    db = SessionLocal()
    try:
        configs = db.query(ReminderConfig).filter(ReminderConfig.enabled == True).all()
        for config in configs:
            try:
                _send_daily_summary_for_user(config.user_id)
            except Exception as e:
                logger.error(f"Failed to send daily summary for user {config.user_id}: {e}")
                # 继续处理其他用户，不中断整个任务
                continue
    except Exception as exc:
        logger.error(f"run_daily_summary_tasks failed: {exc}, retrying...")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


def _check_urgent_reminders() -> None:
    """检查并发送紧急提醒 (同步版本)"""
    db = SessionLocal()
    try:
        configs = db.query(ReminderConfig).filter(ReminderConfig.enabled == True).all()

        for config in configs:
            user = db.query(User).filter(User.id == config.user_id).first()
            if not user:
                continue

            customers = get_pending_follow_customers(db, config.user_id, config)
            urgent = [c for c in customers if c.reminder_reason == "high_intent_overdue"]

            if not urgent:
                continue

            webhook_url = config.webhook_url or settings.WECOM_WEBHOOK_URL
            if not webhook_url:
                continue

            notifier = WeComNotifier(webhook_url)

            for customer in urgent[:3]:
                try:
                    notifier.send_urgent_reminder_sync(
                        user_name=user.username, customer=customer, frontend_url=settings.FRONTEND_URL
                    )

                    db.add(
                        ReminderLog(
                            user_id=config.user_id,
                            customer_id=customer.customer_id,
                            reminder_type="urgent",
                            channel="wecom",
                            status="sent",
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to send urgent reminder: {e}")

            db.commit()
    finally:
        db.close()
