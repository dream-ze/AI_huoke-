"""企业微信机器人通知服务"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx
from app.core.config import settings


@dataclass
class CustomerReminder:
    """待提醒客户信息"""

    customer_id: int
    nickname: str
    intention_level: str
    last_follow_at: Optional[datetime]
    days_since_follow: int
    reminder_reason: str  # new_customer / high_intent_overdue / normal_overdue / scheduled


class WeComNotifier:
    """企业微信机器人通知服务"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or settings.WECOM_WEBHOOK_URL

    async def send_markdown(self, content: str) -> dict:
        """发送 Markdown 消息"""
        if not self.webhook_url:
            raise ValueError("WECOM_WEBHOOK_URL 未配置")

        body = {"msgtype": "markdown", "markdown": {"content": content}}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.webhook_url, json=body)
            resp.raise_for_status()
            return resp.json()

    async def send_daily_summary(
        self, user_name: str, customers: List[CustomerReminder], frontend_url: str = None
    ) -> dict:
        """发送每日跟进汇总"""
        if not customers:
            return {"ok": True, "skipped": True, "reason": "no_customers"}

        # 按优先级分组
        high_intent = [c for c in customers if c.intention_level == "high"]
        new_customers = [c for c in customers if c.reminder_reason == "new_customer"]
        others = [c for c in customers if c not in high_intent and c not in new_customers]

        lines = [f"## 🔔 {user_name}，今日跟进提醒", f"> 您有 **{len(customers)}** 位客户需要跟进", ""]

        if high_intent:
            lines.append("### 🔥 高意向客户（优先处理）")
            for c in high_intent[:5]:
                days_text = f"{c.days_since_follow}天前" if c.days_since_follow > 0 else "待首次联系"
                lines.append(f"- **{c.nickname}** - 上次沟通：{days_text}")
            lines.append("")

        if new_customers:
            lines.append("### 🆕 新客户（待首次联系）")
            for c in new_customers[:5]:
                lines.append(f"- {c.nickname}")
            lines.append("")

        if others:
            lines.append("### 📋 常规跟进")
            for c in others[:5]:
                days_text = f"{c.days_since_follow}天前" if c.days_since_follow > 0 else "待联系"
                lines.append(f"- {c.nickname} - {days_text}")

        if len(customers) > 15:
            lines.append(f"\n*...还有 {len(customers) - 15} 位客户待跟进*")

        if frontend_url:
            lines.append(f"\n👉 [点击查看完整列表]({frontend_url}/customers?filter=pending)")

        content = "\n".join(lines)
        return await self.send_markdown(content)

    async def send_urgent_reminder(self, user_name: str, customer: CustomerReminder, frontend_url: str = None) -> dict:
        """发送紧急跟进提醒"""
        lines = [
            f"## ⚠️ 紧急跟进提醒",
            f"> {user_name}，您有一位高意向客户需要立即跟进",
            "",
            f"**客户：{customer.nickname}**",
            f"- 意向等级：🔥 {customer.intention_level}",
            f"- 上次跟进：{customer.days_since_follow}天前",
        ]

        if frontend_url:
            lines.append(f"\n👉 [立即处理]({frontend_url}/customers/{customer.customer_id})")

        return await self.send_markdown("\n".join(lines))

    async def send_lead_notification(self, user_name: str, lead_info: dict, frontend_url: str = None) -> dict:
        """发送新线索通知"""
        lines = [
            f"## 💎 新线索提醒",
            f"> {user_name}，您有一条新的高意向线索",
            "",
            f"**来源：{lead_info.get('platform', '未知')}**",
            f"- 内容：{lead_info.get('content', '')[:50]}...",
            f"- 意向：{lead_info.get('intention_level', 'medium')}",
        ]

        if frontend_url:
            lines.append(f"\n👉 [查看详情]({frontend_url}/leads/{lead_info.get('lead_id')})")

        return await self.send_markdown("\n".join(lines))

    # ========== 同步版本方法 (用于 Celery 任务) ==========

    def send_markdown_sync(self, content: str) -> dict:
        """发送 Markdown 消息 (同步版本)"""
        if not self.webhook_url:
            raise ValueError("WECOM_WEBHOOK_URL 未配置")

        body = {"msgtype": "markdown", "markdown": {"content": content}}

        with httpx.Client(timeout=10) as client:
            resp = client.post(self.webhook_url, json=body)
            resp.raise_for_status()
            return resp.json()

    def send_daily_summary_sync(
        self, user_name: str, customers: List[CustomerReminder], frontend_url: str = None
    ) -> dict:
        """发送每日跟进汇总 (同步版本)"""
        if not customers:
            return {"ok": True, "skipped": True, "reason": "no_customers"}

        # 按优先级分组
        high_intent = [c for c in customers if c.intention_level == "high"]
        new_customers = [c for c in customers if c.reminder_reason == "new_customer"]
        others = [c for c in customers if c not in high_intent and c not in new_customers]

        lines = [f"## 🔔 {user_name}，今日跟进提醒", f"> 您有 **{len(customers)}** 位客户需要跟进", ""]

        if high_intent:
            lines.append("### 🔥 高意向客户（优先处理）")
            for c in high_intent[:5]:
                days_text = f"{c.days_since_follow}天前" if c.days_since_follow > 0 else "待首次联系"
                lines.append(f"- **{c.nickname}** - 上次沟通：{days_text}")
            lines.append("")

        if new_customers:
            lines.append("### 🆕 新客户（待首次联系）")
            for c in new_customers[:5]:
                lines.append(f"- {c.nickname}")
            lines.append("")

        if others:
            lines.append("### 📋 常规跟进")
            for c in others[:5]:
                days_text = f"{c.days_since_follow}天前" if c.days_since_follow > 0 else "待联系"
                lines.append(f"- {c.nickname} - {days_text}")

        if len(customers) > 15:
            lines.append(f"\n*...还有 {len(customers) - 15} 位客户待跟进*")

        if frontend_url:
            lines.append(f"\n👉 [点击查看完整列表]({frontend_url}/customers?filter=pending)")

        content = "\n".join(lines)
        return self.send_markdown_sync(content)

    def send_urgent_reminder_sync(self, user_name: str, customer: CustomerReminder, frontend_url: str = None) -> dict:
        """发送紧急跟进提醒 (同步版本)"""
        lines = [
            f"## ⚠️ 紧急跟进提醒",
            f"> {user_name}，您有一位高意向客户需要立即跟进",
            "",
            f"**客户：{customer.nickname}**",
            f"- 意向等级：🔥 {customer.intention_level}",
            f"- 上次跟进：{customer.days_since_follow}天前",
        ]

        if frontend_url:
            lines.append(f"\n👉 [立即处理]({frontend_url}/customers/{customer.customer_id})")

        return self.send_markdown_sync("\n".join(lines))

    def send_lead_notification_sync(self, user_name: str, lead_info: dict, frontend_url: str = None) -> dict:
        """发送新线索通知 (同步版本)"""
        lines = [
            f"## 💎 新线索提醒",
            f"> {user_name}，您有一条新的高意向线索",
            "",
            f"**来源：{lead_info.get('platform', '未知')}**",
            f"- 内容：{lead_info.get('content', '')[:50]}...",
            f"- 意向：{lead_info.get('intention_level', 'medium')}",
        ]

        if frontend_url:
            lines.append(f"\n👉 [查看详情]({frontend_url}/leads/{lead_info.get('lead_id')})")

        return self.send_markdown_sync("\n".join(lines))
