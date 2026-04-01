"""企业微信异步任务模块 - 企微通知、消息推送等"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_wecom_notification(self, webhook_url: str, message: str, msg_type: str = "markdown"):
    """异步发送企业微信通知

    Args:
        webhook_url: 企业微信机器人Webhook地址
        message: 消息内容
        msg_type: 消息类型 (markdown/text)

    Returns:
        dict: 发送结果
    """
    logger.info(f"开始发送企微通知: type={msg_type}")

    try:
        import httpx

        if not webhook_url:
            logger.error("Webhook URL为空")
            return {"status": "error", "reason": "webhook_url_empty"}

        body = {"msgtype": msg_type, msg_type: {"content": message}}

        with httpx.Client(timeout=10) as client:
            resp = client.post(webhook_url, json=body)
            resp.raise_for_status()
            result = resp.json()

        if result.get("errcode", 0) not in (0, "0", None):
            logger.error(f"企微API返回错误: {result}")
            return {"status": "error", "reason": "api_error", "detail": result}

        logger.info(f"企微通知发送成功")
        return {"status": "success", "result": result}

    except httpx.TimeoutException:
        logger.error("企微通知发送超时")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"企微通知HTTP错误: {e}")
        raise
    except Exception as exc:
        logger.error(f"企微通知发送失败: error={exc}")
        raise


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_daily_report(self, user_id: int, webhook_url: Optional[str] = None):
    """异步发送每日汇报

    发送用户的每日工作汇报到企业微信

    Args:
        user_id: 用户ID
        webhook_url: Webhook地址（可选，不提供则使用用户配置）

    Returns:
        dict: 发送结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始发送每日汇报: user_id={user_id}")
    db = SessionLocal()
    try:
        from app.core.config import settings
        from app.models.models import ReminderConfig, User

        # 获取用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"用户不存在: user_id={user_id}")
            return {"status": "error", "reason": "user_not_found"}

        # 获取Webhook配置
        if not webhook_url:
            config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()
            webhook_url = config.webhook_url if config else settings.WECOM_WEBHOOK_URL

        if not webhook_url:
            logger.warning(f"用户未配置Webhook: user_id={user_id}")
            return {"status": "error", "reason": "no_webhook_configured"}

        # 生成每日汇报内容
        from datetime import date

        today = date.today()

        # 获取统计数据
        from app.models.models import MvpGenerationResult, MvpMaterialItem
        from sqlalchemy import func

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # 今日素材数
        today_materials = (
            db.query(func.count(MvpMaterialItem.id)).filter(MvpMaterialItem.created_at >= today_start).scalar() or 0
        )

        # 今日生成数
        today_generations = (
            db.query(func.count(MvpGenerationResult.id)).filter(MvpGenerationResult.created_at >= today_start).scalar()
            or 0
        )

        # 待处理收件箱
        from app.models.models import MvpInboxItem

        inbox_pending = db.query(func.count(MvpInboxItem.id)).filter(MvpInboxItem.status == "pending").scalar() or 0

        # 构建汇报消息
        message = f"""## 📊 智获客每日汇报
> **日期**: {today.strftime('%Y年%m月%d日')}
> **用户**: {user.username}

### 今日数据
- 📥 新增素材: **{today_materials}** 条
- ✍️ 内容生成: **{today_generations}** 次
- 📬 待处理收件: **{inbox_pending}** 条

---
💡 [点击进入工作台]({settings.FRONTEND_URL})
"""

        # 发送通知
        result = send_wecom_notification(webhook_url, message, "markdown")

        logger.info(f"每日汇报发送完成: user_id={user_id}")
        return result

    except Exception as exc:
        logger.error(f"每日汇报发送失败: user_id={user_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_generation_complete_notification(self, user_id: int, generation_id: int, title: str, status: str = "success"):
    """异步发送生成完成通知

    当内容生成完成后，通知用户

    Args:
        user_id: 用户ID
        generation_id: 生成任务ID
        title: 内容标题
        status: 生成状态

    Returns:
        dict: 发送结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始发送生成完成通知: user_id={user_id}, generation_id={generation_id}")
    db = SessionLocal()
    try:
        from app.core.config import settings
        from app.models.models import ReminderConfig, User

        # 获取用户配置
        user = db.query(User).filter(User.id == user_id).first()
        config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()

        webhook_url = config.webhook_url if config else settings.WECOM_WEBHOOK_URL

        if not webhook_url:
            logger.debug(f"用户未配置Webhook，跳过通知: user_id={user_id}")
            return {"status": "skipped", "reason": "no_webhook"}

        # 构建通知内容
        status_icon = "✅" if status == "success" else "❌"
        status_text = "成功" if status == "success" else "失败"

        message = f"""{status_icon} **内容生成{status_text}**
> 标题: {title}
> 任务ID: {generation_id}

[查看详情]({settings.FRONTEND_URL}/workbench)
"""

        result = send_wecom_notification(webhook_url, message, "markdown")

        logger.info(f"生成完成通知发送完成: user_id={user_id}")
        return result

    except Exception as exc:
        logger.error(f"生成完成通知发送失败: user_id={user_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_compliance_alert(self, user_id: int, content_id: int, risk_level: str, issues: List[str]):
    """异步发送合规预警通知

    当内容触发合规风险时，发送预警通知

    Args:
        user_id: 用户ID
        content_id: 内容ID
        risk_level: 风险等级 (high/medium/low)
        issues: 风险问题列表

    Returns:
        dict: 发送结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始发送合规预警: user_id={user_id}, content_id={content_id}, risk_level={risk_level}")
    db = SessionLocal()
    try:
        from app.core.config import settings
        from app.models.models import ReminderConfig, User

        user = db.query(User).filter(User.id == user_id).first()
        config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()

        webhook_url = config.webhook_url if config else settings.WECOM_WEBHOOK_URL

        if not webhook_url:
            return {"status": "skipped", "reason": "no_webhook"}

        # 风险等级图标
        risk_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = risk_icons.get(risk_level, "⚠️")

        # 构建问题列表
        issues_text = "\n".join([f"- {issue}" for issue in issues[:5]])  # 最多显示5个

        message = f"""{icon} **合规风险预警**
> 风险等级: **{risk_level.upper()}**
> 内容ID: {content_id}

### 发现的问题:
{issues_text}

⚠️ 请及时处理，避免内容违规风险。
"""

        result = send_wecom_notification(webhook_url, message, "markdown")

        logger.info(f"合规预警发送完成: user_id={user_id}")
        return result

    except Exception as exc:
        logger.error(f"合规预警发送失败: user_id={user_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_batch_notification(self, webhook_url: str, messages: List[Dict[str, Any]]):
    """批量发送企业微信通知

    支持批量发送多条消息，带间隔避免频率限制

    Args:
        webhook_url: Webhook地址
        messages: 消息列表，每条包含 type 和 content

    Returns:
        dict: 批量发送结果
    """
    import time

    logger.info(f"开始批量发送企微通知: {len(messages)}条")

    results = {"total": len(messages), "success": 0, "failed": 0, "details": []}

    for i, msg in enumerate(messages):
        try:
            msg_type = msg.get("type", "markdown")
            content = msg.get("content", "")

            result = send_wecom_notification(webhook_url, content, msg_type)

            if result.get("status") == "success":
                results["success"] += 1
            else:
                results["failed"] += 1

            results["details"].append({"index": i, "status": result.get("status"), "error": result.get("reason")})

            # 避免频率限制，每条消息间隔200ms
            if i < len(messages) - 1:
                time.sleep(0.2)

        except Exception as e:
            logger.error(f"批量通知单条失败: index={i}, error={e}")
            results["failed"] += 1
            results["details"].append({"index": i, "status": "error", "error": str(e)})

    logger.info(f"批量发送完成: 成功{results['success']}, 失败{results['failed']}")
    return results


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
)
def send_system_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    """发送系统告警通知

    发送系统级别的告警通知到管理员群

    Args:
        alert_type: 告警类型 (error/warning/info)
        message: 告警消息
        details: 详细信息

    Returns:
        dict: 发送结果
    """
    from app.core.config import settings

    logger.info(f"开始发送系统告警: type={alert_type}")

    webhook_url = settings.WECOM_WEBHOOK_URL
    if not webhook_url:
        logger.warning("未配置系统告警Webhook，跳过")
        return {"status": "skipped", "reason": "no_webhook"}

    # 告警类型图标
    alert_icons = {"error": "🚨", "warning": "⚠️", "info": "ℹ️"}
    icon = alert_icons.get(alert_type, "📢")

    # 构建详细信息
    details_text = ""
    if details:
        for key, value in details.items():
            details_text += f"\n> {key}: {value}"

    content = f"""{icon} **系统告警**
> 类型: **{alert_type.upper()}**
> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{details_text}

### 消息内容
{message}
"""

    result = send_wecom_notification(webhook_url, content, "markdown")

    logger.info(f"系统告警发送完成: type={alert_type}")
    return result
