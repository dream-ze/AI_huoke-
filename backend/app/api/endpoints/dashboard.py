from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import DashboardSummary, TrendResponse, AICallStatsResponse
from app.services import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get dashboard summary"""
    summary = DashboardService.get_today_summary(db, current_user["user_id"])

    from app.models import RewrittenContent, Customer
    pending_review = db.query(RewrittenContent).filter(
        RewrittenContent.compliance_status == "pending"
    ).count()

    pending_follow = db.query(Customer).filter(
        (Customer.owner_id == current_user["user_id"]) &
        (Customer.customer_status.in_(["new", "pending_follow", "contacted"]))
    ).count()

    summary["pending_follow_count"] = pending_follow
    summary["pending_review_count"] = pending_review

    return summary


@router.get("/trend", response_model=TrendResponse)
def get_trend_data(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get trend data"""
    trends = DashboardService.get_trend_data(db, days)
    return {
        "data": trends,
        "period": f"{days}days"
    }


@router.get("/platform")
def get_platform_analytics(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get platform analytics"""
    analytics = DashboardService.get_platform_analytics(db)
    return analytics


@router.get("/topics")
def get_top_topics(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get top performing topics"""
    topics = DashboardService.get_top_topics(db, limit)
    return topics


@router.get("/high-quality-content")
def get_high_quality_content(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get high-quality customer source content"""
    content = DashboardService.get_high_quality_content(db, limit)
    return content


@router.get("/ai-call-stats", response_model=AICallStatsResponse)
def get_ai_call_stats(
    days: int = Query(7, ge=1, le=90),
    scope: str = Query("me", pattern="^(me|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get daily AI call stats grouped by user."""
    stats = DashboardService.get_ai_call_stats(
        db=db,
        days=days,
        current_user_id=current_user["user_id"],
        scope=scope,
    )
    return {
        "period_days": days,
        "scope": scope,
        "data": stats,
    }
