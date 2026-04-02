from datetime import datetime, timedelta
from typing import Tuple

from app.models import (
    ArkCallLog,
    ContentAsset,
    Conversation,
    Customer,
    FollowUpRecord,
    Lead,
    PublishAccount,
    PublishRecord,
    PublishTask,
    RewrittenContent,
    User,
)
from app.schemas.schemas import (
    AcquisitionLayerMetrics,
    ContentLayerMetrics,
    ConversionLayerMetrics,
    ThreeLayerDashboard,
)
from sqlalchemy import Date, case, desc, func
from sqlalchemy.orm import Session


def _get_period_range(period: str) -> Tuple[datetime, datetime]:
    """根据 period 返回时间范围 (start_time, end_time)

    Args:
        period: today/week/month/all

    Returns:
        tuple: (start_time, end_time)
    """
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now
    else:  # all
        return datetime(1970, 1, 1), now


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

        return (
            [
                {
                    "topic": t[0],
                    "publish_count": t[1] or 0,
                    "total_views": t[2] or 0,
                    "total_wechat_adds": t[3] or 0,
                    "total_valid_leads": t[4] or 0,
                    "wechat_add_rate": round((t[3] or 0) / max(t[2] or 1, 1) * 100, 2),
                    "valid_lead_rate": round((t[4] or 0) / max(t[3] or 1, 1) * 100, 2),
                }
                for t in topics
            ]
            if topics
            else []
        )

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

        return (
            [
                {
                    "title": c[0],
                    "platform": c[1],
                    "total_views": c[2] or 0,
                    "total_wechat_adds": c[3] or 0,
                    "total_valid_leads": c[4] or 0,
                    "valid_lead_rate": round((c[4] or 0) / max(c[3] or 1, 1) * 100, 2),
                }
                for c in content
            ]
            if content
            else []
        )

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

    @staticmethod
    def get_acquisition_metrics(db: Session, owner_id: int | None = None) -> dict:
        """获客层指标 - 带空数据保护"""
        from app.models.crm import Lead

        # 构建基础查询
        base_query = db.query(Lead)
        if owner_id is not None:
            base_query = base_query.filter(Lead.owner_id == owner_id)

        # 各平台线索数
        platform_query = db.query(Lead.platform, func.count(Lead.id).label("count"))
        if owner_id is not None:
            platform_query = platform_query.filter(Lead.owner_id == owner_id)
        platform_leads = platform_query.group_by(Lead.platform).all()

        # 总线索数
        total_leads = base_query.count() or 0

        # 今日新增线索
        today = datetime.utcnow().date()
        today_query = db.query(func.count(Lead.id)).filter(func.cast(Lead.created_at, Date) == today)
        if owner_id is not None:
            today_query = today_query.filter(Lead.owner_id == owner_id)
        today_leads = today_query.scalar() or 0

        # 各平台发布内容的加微率（从PublishedContent统计）
        platform_conversion = []
        try:
            from app.models.published_content import PublishedContent

            content_query = (
                db.query(
                    PublishedContent.platform,
                    func.sum(PublishedContent.views).label("total_views"),
                    func.sum(PublishedContent.wechat_adds).label("total_wechat_adds"),
                    func.sum(PublishedContent.leads_count).label("total_leads"),
                )
                .group_by(PublishedContent.platform)
                .all()
            )

            for c in content_query:
                views = c.total_views or 0
                wechat = c.total_wechat_adds or 0
                rate = round(wechat / max(views, 1) * 100, 2) if views > 0 else 0.0
                platform_conversion.append(
                    {
                        "platform": c.platform,
                        "views": views,
                        "wechat_adds": wechat,
                        "leads": c.total_leads or 0,
                        "wechat_rate": rate,
                    }
                )
        except Exception:
            # 新表尚未创建时返回空列表
            pass

        # ========== 按账号维度的线索数统计 ==========
        leads_by_account = []
        try:
            account_query = db.query(
                PublishAccount.id,
                PublishAccount.account_name,
                PublishAccount.platform,
                func.count(Lead.id).label("lead_count"),
            ).outerjoin(Lead, Lead.publish_account_id == PublishAccount.id)
            if owner_id is not None:
                account_query = account_query.filter(PublishAccount.owner_id == owner_id)
            account_stats = account_query.group_by(
                PublishAccount.id, PublishAccount.account_name, PublishAccount.platform
            ).all()

            for acc in account_stats:
                leads_by_account.append(
                    {
                        "account_id": acc.id,
                        "account_name": acc.account_name,
                        "platform": acc.platform,
                        "lead_count": acc.lead_count or 0,
                    }
                )
        except Exception:
            # 查询失败时返回空列表
            pass

        # ========== 各渠道加微率 ==========
        # 各平台的"已加微信线索数 / 该平台总线索数"
        platform_wechat_rate = []
        try:
            # 按平台统计：总线索数 和 已加微信的线索数(wechat_adds > 0)
            wechat_query = db.query(
                Lead.platform,
                func.count(Lead.id).label("total_count"),
                func.sum(case((Lead.wechat_adds > 0, 1), else_=0)).label("wechat_added_count"),
            )
            if owner_id is not None:
                wechat_query = wechat_query.filter(Lead.owner_id == owner_id)
            wechat_stats = wechat_query.group_by(Lead.platform).all()

            for stat in wechat_stats:
                total = stat.total_count or 0
                wechat_added = int(stat.wechat_added_count or 0)
                rate = round((wechat_added / max(total, 1)) * 100, 2) if total > 0 else 0.0
                platform_wechat_rate.append(
                    {
                        "platform": stat.platform,
                        "total_leads": total,
                        "wechat_added_leads": wechat_added,
                        "wechat_add_rate": rate,
                    }
                )
        except Exception:
            # 查询失败时返回空列表
            pass

        # 空数据提示
        data_hint = ""
        if total_leads == 0:
            data_hint = "暂无线索数据，请先发布内容获取线索"

        return {
            "total_leads": total_leads,
            "today_leads": today_leads,
            "platform_leads": [{"platform": p, "count": c} for p, c in platform_leads] if platform_leads else [],
            "platform_conversion": platform_conversion if platform_conversion else [],
            "leads_by_account": leads_by_account if leads_by_account else [],
            "platform_wechat_rate": platform_wechat_rate if platform_wechat_rate else [],
            "data_hint": data_hint,
        }

    @staticmethod
    def get_conversion_metrics(db: Session, owner_id: int | None = None) -> dict:
        """转化层指标 - 带空数据保护"""
        from app.models.crm import Customer

        today = datetime.utcnow().date()

        # ABCD线索占比（qualification_score: A/B/C/D）
        grade_query = db.query(Customer.qualification_score, func.count(Customer.id).label("count")).filter(
            Customer.qualification_score.isnot(None)
        )
        if owner_id is not None:
            grade_query = grade_query.filter(Customer.owner_id == owner_id)
        grade_distribution = grade_query.group_by(Customer.qualification_score).all()

        total_graded = sum(c for _, c in grade_distribution) if grade_distribution else 0
        grade_stats = []
        for grade, count in grade_distribution:
            grade_stats.append(
                {
                    "grade": grade,
                    "count": count,
                    "percentage": round(count / max(total_graded, 1) * 100, 1) if total_graded > 0 else 0.0,
                }
            )

        # 总客户数
        customer_query = db.query(func.count(Customer.id))
        if owner_id is not None:
            customer_query = customer_query.filter(Customer.owner_id == owner_id)
        total_customers = customer_query.scalar() or 0

        # 跟进完成率
        total_follow_ups = 0
        today_follow_ups = 0
        try:
            total_follow_query = db.query(func.count(FollowUpRecord.id))
            if owner_id is not None:
                total_follow_query = total_follow_query.filter(FollowUpRecord.follow_by == owner_id)
            total_follow_ups = total_follow_query.scalar() or 0

            # 今日跟进数
            today_follow_query = db.query(func.count(FollowUpRecord.id)).filter(
                func.cast(FollowUpRecord.created_at, Date) == today
            )
            if owner_id is not None:
                today_follow_query = today_follow_query.filter(FollowUpRecord.follow_by == owner_id)
            today_follow_ups = today_follow_query.scalar() or 0
        except Exception:
            # 新表尚未创建时返回0
            pass

        # ========== 首次响应平均时长 ==========
        # 从 lead 创建时间到第一次 follow_up 记录的时间差（分钟）
        avg_first_response_minutes = 0.0
        try:
            # 查询每个 lead 的首次跟进时间
            # 子查询：获取每个 lead 的最早跟进记录
            first_follow_up_subq = (
                db.query(FollowUpRecord.lead_id, func.min(FollowUpRecord.follow_date).label("first_follow_date"))
                .filter(FollowUpRecord.lead_id.isnot(None))
                .group_by(FollowUpRecord.lead_id)
                .subquery()
            )

            # 关联 Lead 表，计算时间差
            response_query = db.query(
                Lead.id, Lead.created_at.label("lead_created_at"), first_follow_up_subq.c.first_follow_date
            ).join(first_follow_up_subq, Lead.id == first_follow_up_subq.c.lead_id)
            if owner_id is not None:
                response_query = response_query.filter(Lead.owner_id == owner_id)

            response_records = response_query.all()

            if response_records:
                total_minutes = 0.0
                valid_count = 0
                for record in response_records:
                    if record.lead_created_at and record.first_follow_date:
                        diff = record.first_follow_date - record.lead_created_at
                        minutes = diff.total_seconds() / 60
                        if minutes >= 0:  # 只计算正数（跟进时间在创建之后）
                            total_minutes += minutes
                            valid_count += 1
                if valid_count > 0:
                    avg_first_response_minutes = round(total_minutes / valid_count, 2)
        except Exception:
            # 查询失败时返回0
            pass

        # ========== 成交转化率 ==========
        # status='converted' 的客户数 / 总客户数
        conversion_rate = 0.0
        converted_customers = 0
        try:
            converted_query = db.query(func.count(Customer.id)).filter(Customer.customer_status == "converted")
            if owner_id is not None:
                converted_query = converted_query.filter(Customer.owner_id == owner_id)
            converted_customers = converted_query.scalar() or 0

            conversion_rate = round((converted_customers / max(total_customers, 1)) * 100, 2)
        except Exception:
            # 查询失败时返回0
            pass

        # 空数据提示
        data_hint = ""
        if total_customers == 0:
            data_hint = "暂无客户数据，线索转化后将自动统计"

        return {
            "total_customers": total_customers,
            "grade_distribution": grade_stats if grade_stats else [],
            "total_follow_ups": total_follow_ups,
            "today_follow_ups": today_follow_ups,
            "avg_first_response_minutes": avg_first_response_minutes,
            "conversion_rate": conversion_rate,
            "converted_customers": converted_customers,
            "data_hint": data_hint,
        }

    @staticmethod
    def get_full_dashboard(db: Session, owner_id: int | None = None) -> dict:
        """综合三层看板 - 带数据完整性状态提示"""
        # 内容层指标（复用现有方法）
        content_metrics = DashboardService.get_business_metrics(db, owner_id) if owner_id else {}

        # 获客层
        acquisition_metrics = DashboardService.get_acquisition_metrics(db, owner_id)

        # 转化层
        conversion_metrics = DashboardService.get_conversion_metrics(db, owner_id)

        # 数据就绪状态判断
        content_ready = bool(content_metrics.get("published_this_week", 0) > 0)
        acquisition_ready = acquisition_metrics.get("total_leads", 0) > 0
        conversion_ready = conversion_metrics.get("total_customers", 0) > 0

        # 数据完整性状态
        data_status = {
            "content_layer": {
                "ready": content_ready,
                "hint": "" if content_ready else "暂无发布数据，建议先配置发布账号并创建内容",
            },
            "acquisition_layer": {
                "ready": acquisition_ready,
                "hint": "" if acquisition_ready else "暂无线索数据，建议先配置发布账号并发布内容",
            },
            "conversion_layer": {
                "ready": conversion_ready,
                "hint": "" if conversion_ready else "暂无客户数据，线索转化后将自动统计",
            },
        }

        return {
            "content": content_metrics,
            "acquisition": acquisition_metrics,
            "conversion": conversion_metrics,
            "data_status": data_status,
        }

    @staticmethod
    def get_content_layer_metrics(db: Session, owner_id: int, period: str = "today") -> ContentLayerMetrics:
        """内容层指标

        Args:
            db: 数据库会话
            owner_id: 用户ID
            period: 统计周期 (today/week/month/all)

        Returns:
            ContentLayerMetrics: 内容层指标数据
        """
        from app.models.mvp import MvpGenerationResult, MvpKnowledgeItem, MvpMaterialItem

        start_time, end_time = _get_period_range(period)

        # 1. 今日生成数 - 统计 mvp_generation_results 在时间范围内创建的记录数
        today_generation_count = (
            db.query(func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.created_at >= start_time)
            .filter(MvpGenerationResult.created_at <= end_time)
            .scalar()
            or 0
        )

        # 2. 合规通过率 - 通过合规/总检测 * 100
        total_compliance_checked = (
            db.query(func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.compliance_status.isnot(None))
            .filter(MvpGenerationResult.created_at >= start_time)
            .filter(MvpGenerationResult.created_at <= end_time)
            .scalar()
            or 0
        )
        compliance_passed = (
            db.query(func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.compliance_status == "passed")
            .filter(MvpGenerationResult.created_at >= start_time)
            .filter(MvpGenerationResult.created_at <= end_time)
            .scalar()
            or 0
        )
        compliance_pass_rate = (
            round((compliance_passed / total_compliance_checked) * 100, 2) if total_compliance_checked > 0 else 0.0
        )

        # 3. 采纳率 - 被用户采纳的/总生成 * 100
        # 通过 MvpGenerationFeedback 表统计 adopted 状态
        try:
            from app.models.mvp import MvpGenerationFeedback

            total_feedback = (
                db.query(func.count(MvpGenerationFeedback.id))
                .filter(MvpGenerationFeedback.created_at >= start_time)
                .filter(MvpGenerationFeedback.created_at <= end_time)
                .scalar()
                or 0
            )
            adopted_count = (
                db.query(func.count(MvpGenerationFeedback.id))
                .filter(MvpGenerationFeedback.feedback_type == "adopted")
                .filter(MvpGenerationFeedback.created_at >= start_time)
                .filter(MvpGenerationFeedback.created_at <= end_time)
                .scalar()
                or 0
            )
            adoption_rate = round((adopted_count / total_feedback) * 100, 2) if total_feedback > 0 else 0.0
        except Exception:
            adoption_rate = 0.0

        # 4. 发布率 - 已发布/总生成 * 100
        # 通过 PublishTask 统计已发布的数量
        total_generation = today_generation_count
        published_count = (
            db.query(func.count(PublishTask.id))
            .filter(PublishTask.owner_id == owner_id)
            .filter(PublishTask.status.in_(["submitted", "closed"]))
            .filter(PublishTask.posted_at >= start_time)
            .filter(PublishTask.posted_at <= end_time)
            .scalar()
            or 0
        )
        publish_rate = round((published_count / total_generation) * 100, 2) if total_generation > 0 else 0.0

        # 5. 素材总数 - MvpMaterialItem 总数
        total_materials = db.query(func.count(MvpMaterialItem.id)).scalar() or 0

        # 6. 知识库条目数 - MvpKnowledgeItem 总数
        knowledge_items = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

        return ContentLayerMetrics(
            today_generation_count=today_generation_count,
            compliance_pass_rate=compliance_pass_rate,
            adoption_rate=adoption_rate,
            publish_rate=publish_rate,
            total_materials=total_materials,
            knowledge_items=knowledge_items,
        )

    @staticmethod
    def get_acquisition_layer_metrics_enhanced(
        db: Session, owner_id: int, period: str = "week"
    ) -> AcquisitionLayerMetrics:
        """获客层指标（增强版）

        Args:
            db: 数据库会话
            owner_id: 用户ID
            period: 统计周期 (today/week/month/all)

        Returns:
            AcquisitionLayerMetrics: 获客层指标数据
        """
        from app.models.attribution import LeadSourceAttribution

        start_time, end_time = _get_period_range(period)

        # 基础查询过滤
        base_query = db.query(Lead).filter(Lead.owner_id == owner_id)
        period_query = base_query.filter(Lead.created_at >= start_time).filter(Lead.created_at <= end_time)

        # 1. 总线索数
        total_leads = period_query.count() or 0

        # 2. 各平台线索数
        platform_leads = (
            db.query(Lead.platform, func.count(Lead.id).label("count"))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_time)
            .filter(Lead.created_at <= end_time)
            .group_by(Lead.platform)
            .all()
        )
        leads_by_platform = [{"platform": p, "count": c} for p, c in platform_leads] if platform_leads else []

        # 3. 各账号线索数 - 通过 lead_source_attributions JOIN publish_accounts 统计
        leads_by_account = []
        try:
            account_leads = (
                db.query(PublishAccount.account_name, func.count(Lead.id).label("count"))
                .join(LeadSourceAttribution, LeadSourceAttribution.publish_account_id == PublishAccount.id)
                .join(Lead, Lead.id == LeadSourceAttribution.lead_id)
                .filter(Lead.owner_id == owner_id)
                .filter(Lead.created_at >= start_time)
                .filter(Lead.created_at <= end_time)
                .group_by(PublishAccount.account_name)
                .all()
            )
            leads_by_account = (
                [{"account_name": name, "count": c} for name, c in account_leads] if account_leads else []
            )
        except Exception:
            # 表不存在或查询失败
            pass

        # 4. 各主题线索数 - 通过 lead_source_attributions 的 topic_tags 统计
        leads_by_topic = []
        try:
            # 从 LeadSourceAttribution 的 JSON 字段中提取主题
            # 简化处理：按 PublishTask 的 content_text 关键词分类
            topic_leads = (
                db.query(PublishTask.task_title, func.count(Lead.id).label("count"))
                .join(Lead, Lead.publish_task_id == PublishTask.id)
                .filter(Lead.owner_id == owner_id)
                .filter(Lead.created_at >= start_time)
                .filter(Lead.created_at <= end_time)
                .group_by(PublishTask.task_title)
                .limit(10)
                .all()
            )
            leads_by_topic = (
                [{"topic": title[:50] if title else "未知", "count": c} for title, c in topic_leads]
                if topic_leads
                else []
            )
        except Exception:
            pass

        # 5. 加微率 - 有微信的线索占比
        leads_with_wechat = period_query.filter(Lead.wechat_adds > 0).count() or 0
        wechat_add_rate = round((leads_with_wechat / total_leads) * 100, 2) if total_leads > 0 else 0.0

        # 6. 留资率 - 有联系方式的线索占比 (通过 Customer 表关联)
        try:
            leads_with_contact = (
                db.query(func.count(func.distinct(Lead.id)))
                .join(Customer, Customer.lead_id == Lead.id)
                .filter(Lead.owner_id == owner_id)
                .filter(Lead.created_at >= start_time)
                .filter(Lead.created_at <= end_time)
                .filter((Customer.phone.isnot(None)) | (Customer.wechat_id.isnot(None)))
                .scalar()
                or 0
            )
            contact_rate = round((leads_with_contact / total_leads) * 100, 2) if total_leads > 0 else 0.0
        except Exception:
            contact_rate = 0.0

        return AcquisitionLayerMetrics(
            total_leads=total_leads,
            leads_by_platform=leads_by_platform,
            leads_by_account=leads_by_account,
            leads_by_topic=leads_by_topic,
            wechat_add_rate=wechat_add_rate,
            contact_rate=contact_rate,
        )

    @staticmethod
    def get_conversion_layer_metrics_enhanced(
        db: Session, owner_id: int, period: str = "month"
    ) -> ConversionLayerMetrics:
        """转化层指标（增强版）

        Args:
            db: 数据库会话
            owner_id: 用户ID
            period: 统计周期 (today/week/month/all)

        Returns:
            ConversionLayerMetrics: 转化层指标数据
        """
        start_time, end_time = _get_period_range(period)

        # 1. ABCD线索占比 - 按 Customer.qualification_score 分组统计
        grade_query = (
            db.query(Customer.qualification_score, func.count(Customer.id).label("count"))
            .filter(Customer.owner_id == owner_id)
            .filter(Customer.qualification_score.isnot(None))
            .filter(Customer.created_at >= start_time)
            .filter(Customer.created_at <= end_time)
            .group_by(Customer.qualification_score)
            .all()
        )

        total_graded = sum(c for _, c in grade_query) if grade_query else 0
        grade_distribution = {}
        for grade, count in grade_query:
            if grade and total_graded > 0:
                grade_distribution[grade] = round((count / total_graded) * 100, 2)

        # 确保ABCD都有值
        for g in ["A", "B", "C", "D"]:
            if g not in grade_distribution:
                grade_distribution[g] = 0.0

        # 2. 平均首次响应时长(小时) - 从线索创建到第一条 follow_up_record 的平均时间差
        avg_first_response_hours = 0.0
        try:
            # 子查询：获取每个 lead 的最早跟进记录
            first_follow_subq = (
                db.query(FollowUpRecord.lead_id, func.min(FollowUpRecord.follow_date).label("first_follow_date"))
                .filter(FollowUpRecord.lead_id.isnot(None))
                .group_by(FollowUpRecord.lead_id)
                .subquery()
            )

            response_query = (
                db.query(Lead.id, Lead.created_at.label("lead_created_at"), first_follow_subq.c.first_follow_date)
                .join(first_follow_subq, Lead.id == first_follow_subq.c.lead_id)
                .filter(Lead.owner_id == owner_id)
                .filter(Lead.created_at >= start_time)
                .filter(Lead.created_at <= end_time)
                .all()
            )

            if response_query:
                total_hours = 0.0
                valid_count = 0
                for record in response_query:
                    if record.lead_created_at and record.first_follow_date:
                        diff = record.first_follow_date - record.lead_created_at
                        hours = diff.total_seconds() / 3600
                        if hours >= 0:
                            total_hours += hours
                            valid_count += 1
                if valid_count > 0:
                    avg_first_response_hours = round(total_hours / valid_count, 2)
        except Exception:
            pass

        # 3. 跟进完成率 - 有跟进记录的线索占比
        total_leads = (
            db.query(func.count(Lead.id))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_time)
            .filter(Lead.created_at <= end_time)
            .scalar()
            or 0
        )

        followup_completion_rate = 0.0
        try:
            leads_with_followup = (
                db.query(func.count(func.distinct(FollowUpRecord.lead_id)))
                .join(Lead, Lead.id == FollowUpRecord.lead_id)
                .filter(Lead.owner_id == owner_id)
                .filter(Lead.created_at >= start_time)
                .filter(Lead.created_at <= end_time)
                .scalar()
                or 0
            )
            followup_completion_rate = round((leads_with_followup / total_leads) * 100, 2) if total_leads > 0 else 0.0
        except Exception:
            pass

        # 4. 成交/放款转化率 - status=converted 的线索占比
        total_customers = (
            db.query(func.count(Customer.id))
            .filter(Customer.owner_id == owner_id)
            .filter(Customer.created_at >= start_time)
            .filter(Customer.created_at <= end_time)
            .scalar()
            or 0
        )

        converted_customers = (
            db.query(func.count(Customer.id))
            .filter(Customer.owner_id == owner_id)
            .filter(Customer.customer_status == "converted")
            .filter(Customer.created_at >= start_time)
            .filter(Customer.created_at <= end_time)
            .scalar()
            or 0
        )

        conversion_rate = round((converted_customers / total_customers) * 100, 2) if total_customers > 0 else 0.0

        # 5. 总转化数
        total_converted = converted_customers

        # 6. 预估收入 - sum(deal_value)
        total_revenue = (
            db.query(func.sum(Customer.deal_value))
            .filter(Customer.owner_id == owner_id)
            .filter(Customer.customer_status == "converted")
            .filter(Customer.created_at >= start_time)
            .filter(Customer.created_at <= end_time)
            .scalar()
            or 0.0
        )

        return ConversionLayerMetrics(
            grade_distribution=grade_distribution,
            avg_first_response_hours=avg_first_response_hours,
            followup_completion_rate=followup_completion_rate,
            conversion_rate=conversion_rate,
            total_converted=total_converted,
            total_revenue=float(total_revenue) if total_revenue else 0.0,
        )

    @staticmethod
    def get_three_layer_dashboard(db: Session, owner_id: int, period: str = "week") -> ThreeLayerDashboard:
        """三层看板汇总

        Args:
            db: 数据库会话
            owner_id: 用户ID
            period: 统计周期 (today/week/month/all)

        Returns:
            ThreeLayerDashboard: 三层看板数据
        """
        content = DashboardService.get_content_layer_metrics(db, owner_id, period)
        acquisition = DashboardService.get_acquisition_layer_metrics_enhanced(db, owner_id, period)
        conversion = DashboardService.get_conversion_layer_metrics_enhanced(db, owner_id, period)

        return ThreeLayerDashboard(
            content=content,
            acquisition=acquisition,
            conversion=conversion,
            period=period,
        )
