"""MVP统计/Dashboard路由模块"""

from app.core.database import get_db
from app.schemas.mvp_schemas import DashboardStatsResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    """获取统计概览"""
    from datetime import datetime, timedelta

    from app.models.models import MvpGenerationResult, MvpInboxItem, MvpKnowledgeItem, MvpMaterialItem
    from sqlalchemy import func

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    inbox_pending = db.query(func.count(MvpInboxItem.id)).filter(MvpInboxItem.biz_status == "pending").scalar() or 0

    material_count = db.query(func.count(MvpMaterialItem.id)).scalar() or 0

    knowledge_count = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

    today_gen = (
        db.query(func.count(MvpGenerationResult.id)).filter(MvpGenerationResult.created_at >= today_start).scalar() or 0
    )

    risk_count = (
        db.query(func.count(MvpGenerationResult.id)).filter(MvpGenerationResult.compliance_status == "blocked").scalar()
        or 0
    )

    recent_gens = db.query(MvpGenerationResult).order_by(MvpGenerationResult.created_at.desc()).limit(5).all()

    recent_mats = db.query(MvpMaterialItem).order_by(MvpMaterialItem.created_at.desc()).limit(5).all()

    return {
        "inbox_pending": inbox_pending,
        "material_count": material_count,
        "knowledge_count": knowledge_count,
        "today_generation_count": today_gen,
        "risk_content_count": risk_count,
        "recent_generations": [
            {
                "id": g.id,
                "title": g.output_title or "",
                "version": g.version,
                "created_at": str(g.created_at) if g.created_at else None,
            }
            for g in recent_gens
        ],
        "recent_materials": [
            {
                "id": m.id,
                "title": m.title,
                "platform": m.platform,
                "created_at": str(m.created_at) if m.created_at else None,
            }
            for m in recent_mats
        ],
    }


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)):
    """获取Dashboard统计数据（AI中枢用）"""
    from datetime import date

    from app.models.models import MvpGenerationResult, MvpInboxItem, MvpKnowledgeItem, MvpMaterialItem
    from sqlalchemy import func, or_

    today = date.today()
    today_str = today.isoformat()

    # 今日采集量（mvp_inbox_items 今日创建的数量）
    today_collected = (
        db.query(func.count(MvpInboxItem.id)).filter(func.date(MvpInboxItem.created_at) == today).scalar() or 0
    )

    # 今日入知识库量（mvp_knowledge_items 今日创建的数量）
    today_knowledge_ingested = (
        db.query(func.count(MvpKnowledgeItem.id)).filter(func.date(MvpKnowledgeItem.created_at) == today).scalar() or 0
    )

    # 今日生成量（mvp_generation_results 今日创建的数量）
    today_generated = (
        db.query(func.count(MvpGenerationResult.id)).filter(func.date(MvpGenerationResult.created_at) == today).scalar()
        or 0
    )

    # 风险文案数（risk_level 为 medium 或 high 的素材数量）
    risk_content_count = (
        db.query(func.count(MvpMaterialItem.id))
        .filter(or_(MvpMaterialItem.risk_level == "medium", MvpMaterialItem.risk_level == "high"))
        .scalar()
        or 0
    )

    # 知识库总量
    total_knowledge = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

    # 素材库总量
    total_materials = db.query(func.count(MvpMaterialItem.id)).scalar() or 0

    return DashboardStatsResponse(
        today_collected=today_collected,
        today_knowledge_ingested=today_knowledge_ingested,
        today_generated=today_generated,
        risk_content_count=risk_content_count,
        total_knowledge=total_knowledge,
        total_materials=total_materials,
        date=today_str,
    )
