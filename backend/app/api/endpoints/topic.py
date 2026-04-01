"""选题规划 API"""

from typing import Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.services.hot_topic_service import HotTopicService
from app.services.topic_planning_service import TopicPlanningService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/topic", tags=["选题规划"])


# === 选题计划 ===
@router.get("/plans")
def list_plans(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """选题计划列表"""
    service = TopicPlanningService(db)
    result = service.list_plans(
        owner_id=current_user["user_id"],
        platform=platform,
        status=status,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("/plans")
def create_plan(
    data: dict,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """创建选题计划"""
    service = TopicPlanningService(db)
    try:
        plan = service.create_plan(
            owner_id=current_user["user_id"],
            data=data,
        )
        return service._serialize_plan(plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """选题计划详情"""
    service = TopicPlanningService(db)
    plan = service.get_plan(plan_id, current_user["user_id"])
    if not plan:
        raise HTTPException(status_code=404, detail="选题计划不存在")
    return service._serialize_plan(plan)


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    data: dict,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新选题计划"""
    service = TopicPlanningService(db)
    try:
        plan = service.update_plan(plan_id, current_user["user_id"], data)
        if not plan:
            raise HTTPException(status_code=404, detail="选题计划不存在")
        return service._serialize_plan(plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """删除选题计划"""
    service = TopicPlanningService(db)
    success = service.delete_plan(plan_id, current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="选题计划不存在")
    return {"message": "删除成功"}


# === 选题创意 ===
@router.get("/ideas")
def list_ideas(
    plan_id: Optional[int] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """选题创意列表"""
    service = TopicPlanningService(db)
    result = service.list_ideas(
        owner_id=current_user["user_id"],
        plan_id=plan_id,
        status=status,
        platform=platform,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("/ideas")
def create_idea(
    data: dict,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """添加选题创意"""
    service = TopicPlanningService(db)
    try:
        idea = service.add_idea(
            owner_id=current_user["user_id"],
            data=data,
        )
        return service._serialize_idea(idea)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/ideas/{idea_id}/status")
def update_idea_status(
    idea_id: int,
    status: str = Query(..., description="创意状态: pending/accepted/rejected/used"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新创意状态"""
    service = TopicPlanningService(db)
    try:
        idea = service.update_idea_status(idea_id, current_user["user_id"], status)
        if not idea:
            raise HTTPException(status_code=404, detail="选题创意不存在")
        return service._serialize_idea(idea)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === 热门话题 ===
@router.get("/hot")
def list_hot_topics(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """热门话题列表"""
    service = HotTopicService(db)
    result = service.list_hot_topics(
        platform=platform,
        category=category,
        limit=limit,
    )
    return {"items": result, "total": len(result)}


@router.post("/hot/discover")
def discover_hot_topics(
    platform: str = Query(..., description="平台: xiaohongshu/douyin/zhihu"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """发现热门话题"""
    service = HotTopicService(db)
    result = service.discover_hot_topics(platform)
    return {"discovered": result, "count": len(result)}


@router.get("/hot/{topic_id}")
def get_hot_topic(
    topic_id: int,
    db: Session = Depends(get_db),
):
    """获取单个热门话题"""
    service = HotTopicService(db)
    topic = service.get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="热门话题不存在")
    return service._serialize_topic(topic)


@router.post("/hot/{topic_id}/trend")
def update_topic_trend(
    topic_id: int,
    heat_score: float = Query(..., description="热度分数"),
    trend_direction: str = Query(..., description="趋势方向: up/down/stable"),
    db: Session = Depends(get_db),
):
    """更新话题趋势"""
    service = HotTopicService(db)
    topic = service.update_trend(topic_id, heat_score, trend_direction)
    if not topic:
        raise HTTPException(status_code=404, detail="热门话题不存在")
    return service._serialize_topic(topic)


@router.delete("/hot/expired")
def cleanup_expired_topics(
    db: Session = Depends(get_db),
):
    """清理过期话题"""
    service = HotTopicService(db)
    count = service.cleanup_expired()
    return {"deleted_count": count, "message": f"已清理 {count} 个过期话题"}


# === AI 推荐 ===
@router.post("/recommend")
def recommend_topics(
    platform: str = Query(..., description="平台: xiaohongshu/douyin/zhihu"),
    audience: Optional[str] = Query(None, description="目标人群"),
    count: int = Query(5, ge=1, le=20, description="推荐数量"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """AI 选题推荐"""
    service = TopicPlanningService(db)
    result = service.generate_recommendations(
        owner_id=current_user["user_id"],
        platform=platform,
        audience=audience,
        count=count,
    )
    return {"recommendations": result, "count": len(result)}


# === 排期日历 ===
@router.get("/calendar")
def get_calendar(
    start_date: str = Query(..., description="开始日期，格式: YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式: YYYY-MM-DD"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """选题排期日历"""
    service = TopicPlanningService(db)
    result = service.get_calendar(
        owner_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
    )
    return {"items": result, "start_date": start_date, "end_date": end_date}
