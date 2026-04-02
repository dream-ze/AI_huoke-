"""
跟进管理服务

提供跟进记录管理和自动提醒功能：
- 创建跟进记录
- 获取待跟进列表
- 自动提醒触发
- 更新跟进结果
- 跟进统计
- 跟进时间线
- 检查逾期跟进
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models.crm import Customer, Lead
from app.models.follow_up import FollowUpRecord
from app.models.workflow import ReminderConfig, ReminderLog
from sqlalchemy import and_, case, desc, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FollowUpService:
    """跟进管理服务"""

    # 跟进类型
    FOLLOW_TYPES = ["phone", "wechat", "sms", "meeting", "other"]

    # 跟进结果
    OUTCOMES = ["valid", "invalid", "need_follow", "converted", "abandoned"]

    # 意向等级优先级映射
    INTENTION_PRIORITY = {"A": 1, "high": 1, "B": 2, "medium": 2, "C": 3, "low": 3, "D": 4}

    @staticmethod
    def create_followup(
        db: Session,
        user_id: int,
        lead_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        follow_type: str = "phone",
        content: str = "",
        next_followup_date: Optional[datetime] = None,
        next_action: Optional[str] = None,
    ) -> FollowUpRecord:
        """
        创建跟进记录

        Args:
            db: 数据库会话
            user_id: 跟进人ID
            lead_id: 线索ID（与customer_id二选一）
            customer_id: 客户ID（与lead_id二选一）
            follow_type: 跟进类型 phone/wechat/sms/meeting/other
            content: 跟进内容
            next_followup_date: 下次跟进时间
            next_action: 下次行动

        Returns:
            FollowUpRecord: 创建的跟进记录
        """
        if not lead_id and not customer_id:
            raise ValueError("必须提供 lead_id 或 customer_id")

        if lead_id:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                raise ValueError(f"线索不存在: {lead_id}")

        if customer_id:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                raise ValueError(f"客户不存在: {customer_id}")

        followup = FollowUpRecord(
            lead_id=lead_id,
            customer_id=customer_id,
            follow_by=user_id,
            follow_date=datetime.utcnow(),
            follow_type=follow_type,
            content=content,
            next_follow_at=next_followup_date,
            next_action=next_action,
        )
        db.add(followup)

        # 更新线索/客户的最后跟进时间
        now = datetime.utcnow()
        if lead_id:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead and lead.status == "new":
                lead.status = "contacted"
            logger.info(f"更新线索 {lead_id} 最后跟进时间")

        if customer_id:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                customer.last_follow_at = now
                if next_followup_date:
                    customer.next_follow_at = next_followup_date
                # 如果是新客户，更新状态
                if customer.customer_status == "new":
                    customer.customer_status = "contacted"
                logger.info(f"更新客户 {customer_id} 最后跟进时间")

        db.commit()
        db.refresh(followup)
        logger.info(f"创建跟进记录成功: id={followup.id}, lead_id={lead_id}, customer_id={customer_id}")
        return followup

    @staticmethod
    def get_pending_followups(
        db: Session,
        user_id: int,
        days_threshold: int = 3,
        limit: int = 50,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取待跟进列表

        查询超过 N 天未跟进的线索和客户，按优先级排序

        Args:
            db: 数据库会话
            user_id: 用户ID
            days_threshold: 超期天数阈值
            limit: 返回数量限制

        Returns:
            Dict: {"leads": [...], "customers": [...]}
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

        # 查询超期未跟进的线索
        leads_query = db.query(Lead).filter(
            Lead.owner_id == user_id,
            Lead.status.in_(["new", "contacted", "qualified"]),
            or_(
                Lead.updated_at < threshold_date,
                Lead.updated_at.is_(None),
            ),
        )
        # 按意向等级排序
        leads = (
            leads_query.order_by(
                case(
                    (Lead.intention_level == "A", 1),
                    (Lead.intention_level == "high", 1),
                    (Lead.intention_level == "B", 2),
                    (Lead.intention_level == "medium", 2),
                    (Lead.intention_level == "C", 3),
                    (Lead.intention_level == "low", 3),
                    else_=4,
                ),
                desc(Lead.created_at),
            )
            .limit(limit)
            .all()
        )

        leads_result = [
            {
                "id": lead.id,
                "type": "lead",
                "title": lead.title,
                "platform": lead.platform,
                "status": lead.status,
                "intention_level": lead.intention_level,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
                "note": lead.note,
            }
            for lead in leads
        ]

        # 查询超期未跟进的客户
        customers_query = db.query(Customer).filter(
            Customer.owner_id == user_id,
            Customer.customer_status.in_(["new", "contacted", "pending_follow"]),
            or_(
                Customer.last_follow_at < threshold_date,
                Customer.last_follow_at.is_(None),
            ),
        )
        customers = (
            customers_query.order_by(
                case(
                    (Customer.intention_level == "A", 1),
                    (Customer.intention_level == "high", 1),
                    (Customer.intention_level == "B", 2),
                    (Customer.intention_level == "medium", 2),
                    (Customer.intention_level == "C", 3),
                    (Customer.intention_level == "low", 3),
                    else_=4,
                ),
                desc(Customer.created_at),
            )
            .limit(limit)
            .all()
        )

        customers_result = [
            {
                "id": customer.id,
                "type": "customer",
                "nickname": customer.nickname,
                "wechat_id": customer.wechat_id,
                "phone": customer.phone,
                "customer_status": customer.customer_status,
                "intention_level": customer.intention_level,
                "last_follow_at": customer.last_follow_at.isoformat() if customer.last_follow_at else None,
                "next_follow_at": customer.next_follow_at.isoformat() if customer.next_follow_at else None,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            }
            for customer in customers
        ]

        logger.info(f"获取待跟进列表: user_id={user_id}, leads={len(leads_result)}, customers={len(customers_result)}")
        return {"leads": leads_result, "customers": customers_result}

    @staticmethod
    def auto_remind(db: Session, user_id: int) -> Dict[str, Any]:
        """
        自动提醒触发

        基于 reminder_configs 配置，检查所有超期未跟进的线索，
        生成 reminder_logs 记录

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Dict: {"reminders": [...], "count": int}
        """
        # 获取用户提醒配置
        config = db.query(ReminderConfig).filter(ReminderConfig.user_id == user_id).first()
        if not config or not config.enabled:
            logger.info(f"用户 {user_id} 未配置提醒或提醒已禁用")
            return {"reminders": [], "count": 0}

        now = datetime.utcnow()
        reminders = []

        # 根据配置计算各类型的超期时间
        new_customer_threshold = now - timedelta(hours=config.new_customer_hours)
        high_intent_threshold = now - timedelta(days=config.high_intent_days)
        normal_threshold = now - timedelta(days=config.normal_days)

        # 查询需要提醒的客户
        customers = (
            db.query(Customer)
            .filter(
                Customer.owner_id == user_id,
                Customer.customer_status.in_(["new", "contacted", "pending_follow"]),
            )
            .all()
        )

        for customer in customers:
            need_remind = False
            reminder_type = None

            # 判断是否需要提醒
            if customer.customer_status == "new":
                if customer.created_at and customer.created_at < new_customer_threshold:
                    need_remind = True
                    reminder_type = "new_customer"
            elif customer.intention_level in ["A", "high"]:
                if not customer.last_follow_at or customer.last_follow_at < high_intent_threshold:
                    need_remind = True
                    reminder_type = "high_intent"
            else:
                if not customer.last_follow_at or customer.last_follow_at < normal_threshold:
                    need_remind = True
                    reminder_type = "normal"

            if need_remind:
                # 检查是否已发送过提醒（避免重复）
                last_log = (
                    db.query(ReminderLog)
                    .filter(
                        ReminderLog.user_id == user_id,
                        ReminderLog.customer_id == customer.id,
                    )
                    .order_by(desc(ReminderLog.created_at))
                    .first()
                )

                # 如果最近发送过提醒，跳过
                if last_log and last_log.created_at:
                    if (now - last_log.created_at).total_seconds() < config.urgent_interval_hours * 3600:
                        continue

                # 创建提醒日志
                log = ReminderLog(
                    user_id=user_id,
                    customer_id=customer.id,
                    reminder_type=reminder_type,
                    channel="wecom",
                    status="sent",
                    message_preview=f"客户 {customer.nickname} 需要跟进",
                )
                db.add(log)

                reminders.append(
                    {
                        "customer_id": customer.id,
                        "nickname": customer.nickname,
                        "reminder_type": reminder_type,
                        "last_follow_at": customer.last_follow_at.isoformat() if customer.last_follow_at else None,
                    }
                )

        db.commit()
        logger.info(f"自动提醒完成: user_id={user_id}, 发送 {len(reminders)} 条提醒")
        return {"reminders": reminders, "count": len(reminders)}

    @staticmethod
    def update_followup_result(
        db: Session,
        user_id: int,
        followup_id: int,
        result: str,
    ) -> FollowUpRecord:
        """
        更新跟进结果

        Args:
            db: 数据库会话
            user_id: 用户ID
            followup_id: 跟进记录ID
            result: 跟进结果 valid/invalid/need_follow/converted/abandoned

        Returns:
            FollowUpRecord: 更新后的跟进记录
        """
        if result not in FollowUpService.OUTCOMES:
            raise ValueError(f"无效的跟进结果: {result}")

        followup = db.query(FollowUpRecord).filter(FollowUpRecord.id == followup_id).first()
        if not followup:
            raise ValueError(f"跟进记录不存在: {followup_id}")

        followup.outcome = result

        # 根据结果更新关联的线索/客户状态
        if result == "converted":
            if followup.lead_id:
                lead = db.query(Lead).filter(Lead.id == followup.lead_id).first()
                if lead:
                    lead.status = "converted"
            if followup.customer_id:
                customer = db.query(Customer).filter(Customer.id == followup.customer_id).first()
                if customer:
                    customer.customer_status = "converted"
        elif result == "abandoned":
            if followup.lead_id:
                lead = db.query(Lead).filter(Lead.id == followup.lead_id).first()
                if lead:
                    lead.status = "lost"
            if followup.customer_id:
                customer = db.query(Customer).filter(Customer.id == followup.customer_id).first()
                if customer:
                    customer.customer_status = "lost"
        elif result == "valid":
            if followup.lead_id:
                lead = db.query(Lead).filter(Lead.id == followup.lead_id).first()
                if lead and lead.status == "contacted":
                    lead.status = "qualified"

        db.commit()
        db.refresh(followup)
        logger.info(f"更新跟进结果: followup_id={followup_id}, result={result}")
        return followup

    @staticmethod
    def get_followup_stats(
        db: Session,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        跟进统计

        Args:
            db: 数据库会话
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 统计数据
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # 基础查询
        base_query = db.query(FollowUpRecord).filter(
            FollowUpRecord.follow_by == user_id,
            FollowUpRecord.follow_date >= start_date,
            FollowUpRecord.follow_date <= end_date,
        )

        # 总跟进数
        total_count = base_query.count()

        # 各类型占比
        type_stats = (
            db.query(
                FollowUpRecord.follow_type,
                func.count(FollowUpRecord.id).label("count"),
            )
            .filter(
                FollowUpRecord.follow_by == user_id,
                FollowUpRecord.follow_date >= start_date,
                FollowUpRecord.follow_date <= end_date,
            )
            .group_by(FollowUpRecord.follow_type)
            .all()
        )

        type_distribution = {
            stat.follow_type: {
                "count": stat.count,
                "percentage": round(stat.count / total_count * 100, 2) if total_count > 0 else 0,
            }
            for stat in type_stats
        }

        # 有效跟进率
        valid_outcomes = ["valid", "converted", "need_follow"]
        valid_count = base_query.filter(FollowUpRecord.outcome.in_(valid_outcomes)).count()
        valid_rate = round(valid_count / total_count * 100, 2) if total_count > 0 else 0

        # 转化率
        converted_count = base_query.filter(FollowUpRecord.outcome == "converted").count()
        conversion_rate = round(converted_count / total_count * 100, 2) if total_count > 0 else 0

        # 平均跟进周期（首次跟进到转化的时间）
        converted_followups = base_query.filter(FollowUpRecord.outcome == "converted").all()
        avg_cycle_days = 0
        if converted_followups:
            cycles = []
            for f in converted_followups:
                if f.lead_id:
                    lead = db.query(Lead).filter(Lead.id == f.lead_id).first()
                    if lead and lead.created_at:
                        cycle = (f.follow_date - lead.created_at).days
                        cycles.append(cycle)
                elif f.customer_id:
                    customer = db.query(Customer).filter(Customer.id == f.customer_id).first()
                    if customer and customer.created_at:
                        cycle = (f.follow_date - customer.created_at).days
                        cycles.append(cycle)
            if cycles:
                avg_cycle_days = round(sum(cycles) / len(cycles), 1)

        stats = {
            "total_count": total_count,
            "type_distribution": type_distribution,
            "valid_rate": valid_rate,
            "conversion_rate": conversion_rate,
            "avg_cycle_days": avg_cycle_days,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        logger.info(f"获取跟进统计: user_id={user_id}, stats={stats}")
        return stats

    @staticmethod
    def get_followup_timeline(
        db: Session,
        lead_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        跟进时间线

        按时间倒序返回所有跟进记录

        Args:
            db: 数据库会话
            lead_id: 线索ID
            customer_id: 客户ID
            limit: 返回数量限制

        Returns:
            List: 跟进记录列表
        """
        query = db.query(FollowUpRecord)

        if lead_id:
            query = query.filter(FollowUpRecord.lead_id == lead_id)
        elif customer_id:
            query = query.filter(FollowUpRecord.customer_id == customer_id)
        else:
            raise ValueError("必须提供 lead_id 或 customer_id")

        followups = query.order_by(desc(FollowUpRecord.follow_date)).limit(limit).all()

        timeline = [
            {
                "id": f.id,
                "follow_date": f.follow_date.isoformat() if f.follow_date else None,
                "follow_type": f.follow_type,
                "content": f.content,
                "outcome": f.outcome,
                "next_follow_at": f.next_follow_at.isoformat() if f.next_follow_at else None,
                "next_action": f.next_action,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in followups
        ]

        logger.info(f"获取跟进时间线: lead_id={lead_id}, customer_id={customer_id}, count={len(timeline)}")
        return timeline

    @staticmethod
    def check_overdue_followups(
        db: Session,
        owner_id: int,
        include_customers: bool = True,
        include_leads: bool = True,
    ) -> Dict[str, Any]:
        """
        检查逾期跟进

        返回所有超过计划跟进时间的线索/客户列表

        Args:
            db: 数据库会话
            owner_id: 所有者ID
            include_customers: 是否包含客户
            include_leads: 是否包含线索

        Returns:
            Dict: {"overdue_customers": [...], "overdue_leads": [...], "total": int}
        """
        now = datetime.utcnow()
        overdue_customers = []
        overdue_leads = []

        # 检查逾期的客户
        if include_customers:
            customers = (
                db.query(Customer)
                .filter(
                    Customer.owner_id == owner_id,
                    Customer.customer_status.in_(["new", "contacted", "pending_follow"]),
                    Customer.next_follow_at.isnot(None),
                    Customer.next_follow_at < now,
                )
                .order_by(Customer.next_follow_at)
                .all()
            )

            overdue_customers = [
                {
                    "id": c.id,
                    "type": "customer",
                    "nickname": c.nickname,
                    "wechat_id": c.wechat_id,
                    "phone": c.phone,
                    "intention_level": c.intention_level,
                    "next_follow_at": c.next_follow_at.isoformat() if c.next_follow_at else None,
                    "last_follow_at": c.last_follow_at.isoformat() if c.last_follow_at else None,
                    "overdue_hours": int((now - c.next_follow_at).total_seconds() / 3600) if c.next_follow_at else 0,
                }
                for c in customers
            ]

        # 检查逾期的线索（基于最近跟进记录的 next_follow_at）
        if include_leads:
            # 查询有逾期跟进计划的线索
            overdue_lead_ids = (
                db.query(FollowUpRecord.lead_id)
                .filter(
                    FollowUpRecord.next_follow_at.isnot(None),
                    FollowUpRecord.next_follow_at < now,
                    FollowUpRecord.outcome.is_(None),  # 未完成的跟进
                )
                .distinct()
                .subquery()
            )

            leads = (
                db.query(Lead)
                .filter(
                    Lead.id.in_(overdue_lead_ids),
                    Lead.owner_id == owner_id,
                    Lead.status.in_(["new", "contacted", "qualified"]),
                )
                .all()
            )

            for lead in leads:
                # 获取最近的跟进记录
                last_followup = (
                    db.query(FollowUpRecord)
                    .filter(
                        FollowUpRecord.lead_id == lead.id,
                    )
                    .order_by(desc(FollowUpRecord.follow_date))
                    .first()
                )

                if last_followup and last_followup.next_follow_at:
                    overdue_leads.append(
                        {
                            "id": lead.id,
                            "type": "lead",
                            "title": lead.title,
                            "platform": lead.platform,
                            "status": lead.status,
                            "intention_level": lead.intention_level,
                            "next_follow_at": last_followup.next_follow_at.isoformat(),
                            "overdue_hours": int((now - last_followup.next_follow_at).total_seconds() / 3600),
                        }
                    )

        total = len(overdue_customers) + len(overdue_leads)
        logger.info(f"检查逾期跟进: owner_id={owner_id}, total={total}")

        return {
            "overdue_customers": overdue_customers,
            "overdue_leads": overdue_leads,
            "total": total,
        }
