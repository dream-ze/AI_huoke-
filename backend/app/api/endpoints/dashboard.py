from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import (
    AcquisitionLayerMetrics,
    AICallStatsResponse,
    ContentLayerMetrics,
    ConversionLayerMetrics,
    DashboardSummary,
    ThreeLayerDashboard,
    TrendResponse,
)
from app.services import DashboardService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get dashboard summary"""
    summary = DashboardService.get_today_summary(db, current_user["user_id"])

    from app.models import Customer, RewrittenContent

    pending_review = db.query(RewrittenContent).filter(RewrittenContent.compliance_status == "pending").count()

    pending_follow = (
        db.query(Customer)
        .filter(
            (Customer.owner_id == current_user["user_id"])
            & (Customer.customer_status.in_(["new", "pending_follow", "contacted"]))
        )
        .count()
    )

    summary["pending_follow_count"] = pending_follow
    summary["pending_review_count"] = pending_review

    return summary


@router.get("/trend", response_model=TrendResponse)
def get_trend_data(
    days: int = Query(7, ge=1, le=30), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Get trend data"""
    trends = DashboardService.get_trend_data(db, days)
    return {"data": trends, "period": f"{days}days"}


@router.get("/platform")
def get_platform_analytics(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get platform analytics"""
    analytics = DashboardService.get_platform_analytics(db)
    return analytics


@router.get("/topics")
def get_top_topics(
    limit: int = Query(10, ge=1, le=50), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Get top performing topics"""
    topics = DashboardService.get_top_topics(db, limit)
    return topics


@router.get("/high-quality-content")
def get_high_quality_content(
    limit: int = Query(20, ge=1, le=100), current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """Get high-quality customer source content"""
    content = DashboardService.get_high_quality_content(db, limit)
    return content


@router.get("/ai-call-stats", response_model=AICallStatsResponse)
def get_ai_call_stats(
    days: int = Query(7, ge=1, le=90),
    scope: str = Query("me", pattern="^(me|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
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


@router.get("/metrics")
def get_business_metrics(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取业务核心指标"""
    metrics = DashboardService.get_business_metrics(db, current_user["user_id"])
    return metrics


@router.get("/funnel")
def get_conversion_funnel(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取转化漏斗数据"""
    funnel_data = DashboardService.get_conversion_funnel(db, current_user["user_id"])
    return funnel_data


@router.get("/acquisition")
def get_acquisition_metrics(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获客层指标"""
    metrics = DashboardService.get_acquisition_metrics(db, current_user["user_id"])
    return metrics


@router.get("/conversion")
def get_conversion_metrics(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """转化层指标"""
    metrics = DashboardService.get_conversion_metrics(db, current_user["user_id"])
    return metrics


@router.get("/full")
def get_full_dashboard(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """综合三层看板（内容层+获客层+转化层）"""
    dashboard_data = DashboardService.get_full_dashboard(db, current_user["user_id"])
    return dashboard_data


@router.get("/content-metrics", response_model=ContentLayerMetrics)
def get_content_metrics(
    period: str = Query("today", pattern="^(today|week|month|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """内容层指标

    Args:
        period: 统计周期 (today/week/month/all)
    """
    metrics = DashboardService.get_content_layer_metrics(db, current_user["user_id"], period)
    return metrics


@router.get("/acquisition-metrics", response_model=AcquisitionLayerMetrics)
def get_acquisition_metrics_enhanced(
    period: str = Query("week", pattern="^(today|week|month|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获客层指标

    Args:
        period: 统计周期 (today/week/month/all)
    """
    metrics = DashboardService.get_acquisition_layer_metrics_enhanced(db, current_user["user_id"], period)
    return metrics


@router.get("/conversion-metrics", response_model=ConversionLayerMetrics)
def get_conversion_metrics_enhanced(
    period: str = Query("month", pattern="^(today|week|month|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """转化层指标

    Args:
        period: 统计周期 (today/week/month/all)
    """
    metrics = DashboardService.get_conversion_layer_metrics_enhanced(db, current_user["user_id"], period)
    return metrics


@router.get("/three-layer", response_model=ThreeLayerDashboard)
def get_three_layer_dashboard(
    period: str = Query("week", pattern="^(today|week|month|all)$"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """三层看板汇总

    Args:
        period: 统计周期 (today/week/month/all)
    """
    dashboard = DashboardService.get_three_layer_dashboard(db, current_user["user_id"], period)
    return dashboard
