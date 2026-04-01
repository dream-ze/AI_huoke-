from datetime import datetime, timedelta

from app.models import (
    ArkCallLog,
    ContentAsset,
    Conversation,
    Customer,
    Lead,
    PublishRecord,
    PublishTask,
    RewrittenContent,
    User,
)
from sqlalchemy import Date, case, desc, func
from sqlalchemy.orm import Session


class DashboardService:
    @staticmethod
    def get_today_summary(db: Session, user_id: int) -> dict:
        """Get today's summary statistics"""
        today = datetime.utcnow().date()

        # Today's new customers
        today_customers = (
            db.query(func.count(Customer.id))
            .filter((Customer.owner_id == user_id) & (func.cast(Customer.created_at, Date) == today))
            .scalar()
            or 0
        )

        # Today's publish metrics
        today_publishes = db.query(PublishRecord).filter(func.cast(PublishRecord.publish_time, Date) == today).all()

        today_wechat_adds = sum(p.wechat_adds for p in today_publishes)
        today_leads = sum(p.leads for p in today_publishes)
        today_valid_leads = sum(p.valid_leads for p in today_publishes)
        today_conversions = sum(p.conversions for p in today_publishes)

        return {
            "today_new_customers": today_customers,
            "today_wechat_adds": today_wechat_adds,
            "today_leads": today_leads,
            "today_valid_leads": today_valid_leads,
            "today_conversions": today_conversions,
        }

    @staticmethod
    def get_trend_data(db: Session, days: int = 7) -> list:
        """Get trend data for last N days"""
        trends = []

        for i in range(days - 1, -1, -1):
            date = (datetime.utcnow() - timedelta(days=i)).date()

            day_publishes = db.query(PublishRecord).filter(func.cast(PublishRecord.publish_time, Date) == date).all()

            trend_day = {
                "date": date.isoformat(),
                "publish_count": len(day_publishes),
                "total_views": sum(p.views for p in day_publishes),
                "total_private_messages": sum(p.private_messages for p in day_publishes),
                "total_wechat_adds": sum(p.wechat_adds for p in day_publishes),
                "total_leads": sum(p.leads for p in day_publishes),
                "total_valid_leads": sum(p.valid_leads for p in day_publishes),
                "total_conversions": sum(p.conversions for p in day_publishes),
            }
            trends.append(trend_day)

        return trends

    @staticmethod
    def get_platform_analytics(db: Session) -> list:
        """Get analytics by platform"""
        platforms = db.query(PublishRecord.platform).distinct().all()
        analytics = []

        for (platform,) in platforms:
            records = db.query(PublishRecord).filter(PublishRecord.platform == platform).all()

            platform_data = {
                "platform": platform,
                "publish_count": len(records),
                "total_leads": sum(r.leads for r in records),
                "total_valid_leads": sum(r.valid_leads for r in records),
                "total_conversions": sum(r.conversions for r in records),
            }
            analytics.append(platform_data)

        return sorted(analytics, key=lambda x: x["total_valid_leads"], reverse=True)

    @staticmethod
    def get_top_topics(db: Session, limit: int = 10) -> list:
        """Get top performing topics"""
        # This is a simplified version - you may need to adjust based on your data structure
        topics = (
            db.query(
                ContentAsset.title,
                func.count(PublishRecord.id).label("publish_count"),
                func.sum(PublishRecord.views).label("total_views"),
                func.sum(PublishRecord.wechat_adds).label("total_wechat_adds"),
                func.sum(PublishRecord.valid_leads).label("total_valid_leads"),
            )
            .join(RewrittenContent, RewrittenContent.source_id == ContentAsset.id)
            .join(PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id)
            .group_by(ContentAsset.title)
            .order_by(desc(func.sum(PublishRecord.valid_leads)))
            .limit(limit)
            .all()
        )

        return [
            {
                "topic": t[0],
                "publish_count": t[1],
                "total_views": t[2] or 0,
                "total_wechat_adds": t[3] or 0,
                "total_valid_leads": t[4] or 0,
                "wechat_add_rate": (t[3] or 0) / max(t[2] or 1, 1),
                "valid_lead_rate": (t[4] or 0) / max(t[3] or 1, 1),
            }
            for t in topics
        ]

    @staticmethod
    def get_high_quality_content(db: Session, limit: int = 20) -> list:
        """Get high-quality customer source content"""
        content = (
            db.query(
                ContentAsset.title,
                PublishRecord.platform,
                func.sum(PublishRecord.views).label("total_views"),
                func.sum(PublishRecord.wechat_adds).label("total_wechat_adds"),
                func.sum(PublishRecord.valid_leads).label("total_valid_leads"),
            )
            .join(RewrittenContent, RewrittenContent.source_id == ContentAsset.id)
            .join(PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id)
            .filter(PublishRecord.wechat_adds > 0)
            .group_by(ContentAsset.title, PublishRecord.platform)
            .order_by(desc(func.sum(PublishRecord.valid_leads)))
            .limit(limit)
            .all()
        )

        return [
            {
                "title": c[0],
                "platform": c[1],
                "total_views": c[2] or 0,
                "total_wechat_adds": c[3] or 0,
                "total_valid_leads": c[4] or 0,
                "valid_lead_rate": (c[4] or 0) / max(c[3] or 1, 1),
            }
            for c in content
        ]

    @staticmethod
    def get_ai_call_stats(db: Session, days: int = 7, current_user_id: int | None = None, scope: str = "me") -> list:
        """Aggregate AI call stats by day and user."""
        start_time = datetime.utcnow() - timedelta(days=max(days - 1, 0))
        day_col = func.date(ArkCallLog.created_at)

        failed_count_expr = func.sum(case((ArkCallLog.success.is_(False), 1), else_=0))

        query = (
            db.query(
                day_col.label("date"),
                ArkCallLog.user_id.label("user_id"),
                User.username.label("username"),
                func.count(ArkCallLog.id).label("call_count"),
                failed_count_expr.label("failed_count"),
                func.sum(ArkCallLog.input_tokens).label("input_tokens"),
                func.sum(ArkCallLog.output_tokens).label("output_tokens"),
                func.sum(ArkCallLog.total_tokens).label("total_tokens"),
                func.avg(ArkCallLog.latency_ms).label("avg_latency_ms"),
            )
            .outerjoin(User, User.id == ArkCallLog.user_id)
            .filter(ArkCallLog.created_at >= start_time)
        )

        if scope == "me" and current_user_id is not None:
            query = query.filter(ArkCallLog.user_id == current_user_id)

        rows = (
            query.group_by(
                day_col,
                ArkCallLog.user_id,
                User.username,
            )
            .order_by(
                day_col.desc(),
                ArkCallLog.user_id.asc(),
            )
            .all()
        )

        result = []
        for row in rows:
            call_count = int(row.call_count or 0)
            failed_count = int(row.failed_count or 0)
            failure_rate = round((failed_count / call_count) * 100, 2) if call_count > 0 else 0.0
            result.append(
                {
                    "date": str(row.date),
                    "user_id": row.user_id,
                    "username": row.username,
                    "call_count": call_count,
                    "failed_count": failed_count,
                    "failure_rate": failure_rate,
                    "input_tokens": int(row.input_tokens or 0),
                    "output_tokens": int(row.output_tokens or 0),
                    "total_tokens": int(row.total_tokens or 0),
                    "avg_latency_ms": round(float(row.avg_latency_ms or 0.0), 2),
                }
            )
        return result

    @staticmethod
    def get_business_metrics(db: Session, user_id: int) -> dict:
        """获取业务核心指标"""
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # 本周一

        # 今日新增线索数
        leads_today = (
            db.query(func.count(Lead.id))
            .filter((Lead.owner_id == user_id) & (func.cast(Lead.created_at, Date) == today))
            .scalar()
            or 0
        )

        # 高意向线索数 (intention_level = 'high')
        high_intent_leads = (
            db.query(func.count(Lead.id)).filter((Lead.owner_id == user_id) & (Lead.intention_level == "high")).scalar()
            or 0
        )

        # AI会话处理率
        total_conversations = (
            db.query(func.count(Conversation.id))
            .filter(Conversation.status.in_(["active", "closed", "takeover"]))
            .scalar()
            or 0
        )
        ai_handled_conversations = (
            db.query(func.count(Conversation.id)).filter(Conversation.ai_handled.is_(True)).scalar() or 0
        )
        ai_handle_rate = (
            round((ai_handled_conversations / total_conversations) * 100, 2) if total_conversations > 0 else 0.0
        )

        # 人工接管率
        takeover_conversations = (
            db.query(func.count(Conversation.id)).filter(Conversation.status == "takeover").scalar() or 0
        )
        takeover_rate = (
            round((takeover_conversations / total_conversations) * 100, 2) if total_conversations > 0 else 0.0
        )

        # 内容到线索转化率
        # 基于PublishRecord统计：发布内容带来的线索
        content_leads_data = (
            db.query(
                func.sum(PublishRecord.leads).label("total_leads"),
                func.count(PublishRecord.id).label("total_publishes"),
            )
            .select_from(ContentAsset)
            .join(RewrittenContent, RewrittenContent.source_id == ContentAsset.id)
            .join(PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id)
            .filter(ContentAsset.owner_id == user_id)
            .first()
        )

        total_content_leads = content_leads_data.total_leads or 0 if content_leads_data else 0
        total_publishes = content_leads_data.total_publishes or 0 if content_leads_data else 0
        content_to_lead_rate = round((total_content_leads / max(total_publishes, 1)) * 100, 2)

        # 本周发布数 (基于PublishTask)
        published_this_week = (
            db.query(func.count(PublishTask.id))
            .filter(
                (PublishTask.owner_id == user_id)
                & (PublishTask.status.in_(["submitted", "closed"]))
                & (func.cast(PublishTask.posted_at, Date) >= week_start)
            )
            .scalar()
            or 0
        )

        # 本周线索数
        leads_this_week = (
            db.query(func.count(Lead.id))
            .filter((Lead.owner_id == user_id) & (func.cast(Lead.created_at, Date) >= week_start))
            .scalar()
            or 0
        )

        return {
            "leads_today": leads_today,
            "high_intent_leads": high_intent_leads,
            "ai_handle_rate": ai_handle_rate,
            "takeover_rate": takeover_rate,
            "content_to_lead_rate": content_to_lead_rate,
            "published_this_week": published_this_week,
            "leads_this_week": leads_this_week,
        }

    @staticmethod
    def get_conversion_funnel(db: Session, user_id: int) -> dict:
        """获取转化漏斗数据"""
        # 阶段1: 内容生成 (ContentAsset)
        content_generated = db.query(func.count(ContentAsset.id)).filter(ContentAsset.owner_id == user_id).scalar() or 0

        # 阶段2: 已发布 (PublishRecord关联的内容)
        content_published = (
            db.query(func.count(PublishRecord.id))
            .filter(
                PublishRecord.id.in_(
                    db.query(PublishRecord.id)
                    .select_from(ContentAsset)
                    .join(RewrittenContent, RewrittenContent.source_id == ContentAsset.id)
                    .join(PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id)
                    .filter(ContentAsset.owner_id == user_id)
                )
            )
            .scalar()
            or 0
        )

        # 阶段3: 获得线索 (Lead)
        leads_generated = db.query(func.count(Lead.id)).filter(Lead.owner_id == user_id).scalar() or 0

        # 阶段4: 转化客户 (Customer)
        customers_converted = (
            db.query(func.count(Customer.id))
            .filter((Customer.owner_id == user_id) & (Customer.customer_status.in_(["qualified", "converted"])))
            .scalar()
            or 0
        )

        # 阶段5: 成交 (Customer with deal_value > 0)
        deals_closed = (
            db.query(func.count(Customer.id))
            .filter((Customer.owner_id == user_id) & (Customer.deal_value > 0))
            .scalar()
            or 0
        )

        # 构建漏斗数据
        funnel = {
            "content_generated": content_generated,
            "content_published": content_published,
            "leads_generated": leads_generated,
            "customers_converted": customers_converted,
            "deals_closed": deals_closed,
        }

        # 计算各阶段转化率
        conversion_rates = {
            "content_to_publish": round((content_published / max(content_generated, 1)) * 100, 2),
            "publish_to_lead": round((leads_generated / max(content_published, 1)) * 100, 2),
            "lead_to_customer": round((customers_converted / max(leads_generated, 1)) * 100, 2),
            "customer_to_deal": round((deals_closed / max(customers_converted, 1)) * 100, 2),
            "overall_conversion": round((deals_closed / max(content_generated, 1)) * 100, 2),
        }

        return {
            "funnel": funnel,
            "conversion_rates": conversion_rates,
        }
