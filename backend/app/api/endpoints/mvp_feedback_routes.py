"""MVP反馈闭环路由模块"""

from app.core.database import get_db
from app.schemas.mvp_schemas import FeedbackResponse, FeedbackStatsResponse, FeedbackSubmitRequest
from app.services.feedback_service import FeedbackService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackSubmitRequest, db: Session = Depends(get_db)):
    """
    提交生成结果反馈

    - 记录反馈类型（采纳/修改后采纳/拒绝）
    - 更新关联知识条目的质量评分
    - 支持评分和标签
    """
    service = FeedbackService(db)
    result = await service.submit_feedback(
        generation_id=req.generation_id,
        query=req.query,
        generated_text=req.generated_text,
        feedback_type=req.feedback_type,
        modified_text=req.modified_text,
        rating=req.rating,
        feedback_tags=req.feedback_tags,
        knowledge_ids_used=req.knowledge_ids_used,
    )
    return FeedbackResponse(**result)


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    获取反馈统计

    - 采纳率、修改率、拒绝率
    - 平均评分
    """
    service = FeedbackService(db)
    stats = await service.get_feedback_stats(days)
    return FeedbackStatsResponse(**stats)


@router.get("/knowledge/quality/rankings")
async def get_quality_rankings(
    limit: int = Query(20, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """
    获取知识库质量排行榜

    - 按质量评分排序
    - 显示引用次数、正负面反馈等
    """
    service = FeedbackService(db)
    items = await service.get_quality_rankings(limit, order)
    return {"items": items, "total": len(items)}


@router.get("/knowledge/quality/suggestions")
async def get_learning_suggestions(db: Session = Depends(get_db)):
    """
    获取持续学习建议

    - 高评价知识条目 → 建议权重提升
    - 低评价知识条目 → 建议降权或移除
    - 用户修改模式分析 → 建议内容调整方向
    """
    service = FeedbackService(db)
    suggestions = await service.get_learning_suggestions()
    return suggestions


@router.post("/knowledge/quality/adjust")
async def apply_weight_adjustment(db: Session = Depends(get_db)):
    """
    应用权重调整

    - quality_score > 0.8: 检索时权重 boost 1.5x
    - quality_score < 0.3: 检索时降权 0.5x
    - reference_count == 0 且 创建超30天: 标记为冷数据
    """
    service = FeedbackService(db)
    result = await service.apply_weight_adjustment()
    return result


@router.get("/feedback/tags")
async def get_feedback_tags():
    """获取可用的反馈标签选项"""
    from app.services.feedback_service import FeedbackService

    return {"tags": FeedbackService.FEEDBACK_TAGS_OPTIONS}
