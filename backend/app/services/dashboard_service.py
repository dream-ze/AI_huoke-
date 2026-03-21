from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case, Date
from app.models import PublishRecord, RewrittenContent, ContentAsset, Customer, ArkCallLog, User
from datetime import datetime, timedelta


class DashboardService:
    @staticmethod
    def get_today_summary(db: Session, user_id: int) -> dict:
        """Get today's summary statistics"""
        today = datetime.utcnow().date()
        
        # Today's new customers
        today_customers = db.query(func.count(Customer.id)).filter(
            (Customer.owner_id == user_id) &
            (func.cast(Customer.created_at, Date) == today)
        ).scalar() or 0
        
        # Today's publish metrics
        today_publishes = db.query(PublishRecord).filter(
            func.cast(PublishRecord.publish_time, Date) == today
        ).all()
        
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
            
            day_publishes = db.query(PublishRecord).filter(
                func.cast(PublishRecord.publish_time, Date) == date
            ).all()
            
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
            records = db.query(PublishRecord).filter(
                PublishRecord.platform == platform
            ).all()
            
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
        topics = db.query(
            ContentAsset.title,
            func.count(PublishRecord.id).label("publish_count"),
            func.sum(PublishRecord.views).label("total_views"),
            func.sum(PublishRecord.wechat_adds).label("total_wechat_adds"),
            func.sum(PublishRecord.valid_leads).label("total_valid_leads"),
        ).join(
            RewrittenContent, RewrittenContent.source_id == ContentAsset.id
        ).join(
            PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id
        ).group_by(
            ContentAsset.title
        ).order_by(
            desc(func.sum(PublishRecord.valid_leads))
        ).limit(limit).all()
        
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
        content = db.query(
            ContentAsset.title,
            PublishRecord.platform,
            func.sum(PublishRecord.views).label("total_views"),
            func.sum(PublishRecord.wechat_adds).label("total_wechat_adds"),
            func.sum(PublishRecord.valid_leads).label("total_valid_leads"),
        ).join(
            RewrittenContent, RewrittenContent.source_id == ContentAsset.id
        ).join(
            PublishRecord, PublishRecord.rewritten_content_id == RewrittenContent.id
        ).filter(
            PublishRecord.wechat_adds > 0
        ).group_by(
            ContentAsset.title, PublishRecord.platform
        ).order_by(
            desc(func.sum(PublishRecord.valid_leads))
        ).limit(limit).all()
        
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

        failed_count_expr = func.sum(
            case((ArkCallLog.success.is_(False), 1), else_=0)
        )

        query = db.query(
            day_col.label("date"),
            ArkCallLog.user_id.label("user_id"),
            User.username.label("username"),
            func.count(ArkCallLog.id).label("call_count"),
            failed_count_expr.label("failed_count"),
            func.sum(ArkCallLog.input_tokens).label("input_tokens"),
            func.sum(ArkCallLog.output_tokens).label("output_tokens"),
            func.sum(ArkCallLog.total_tokens).label("total_tokens"),
            func.avg(ArkCallLog.latency_ms).label("avg_latency_ms"),
        ).outerjoin(
            User, User.id == ArkCallLog.user_id
        ).filter(
            ArkCallLog.created_at >= start_time
        )

        if scope == "me" and current_user_id is not None:
            query = query.filter(ArkCallLog.user_id == current_user_id)

        rows = query.group_by(
            day_col,
            ArkCallLog.user_id,
            User.username,
        ).order_by(
            day_col.desc(),
            ArkCallLog.user_id.asc(),
        ).all()

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
