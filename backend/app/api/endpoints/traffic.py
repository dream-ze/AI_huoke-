"""引流策略 API"""

from typing import Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.services.traffic_strategy_service import TrafficStrategyService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/traffic", tags=["引流策略"])


@router.get("/strategies")
def list_strategies(
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取策略列表"""
    service = TrafficStrategyService(db)
    result = service.list_strategies(
        owner_id=current_user["user_id"], platform=platform, status=status, page=page, page_size=page_size
    )
    return result


@router.post("/strategies")
def create_strategy(data: dict, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """创建策略"""
    service = TrafficStrategyService(db)
    result = service.create_strategy(owner_id=current_user["user_id"], data=data)
    return result


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: int, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取单个策略详情"""
    service = TrafficStrategyService(db)
    result = service.get_strategy(strategy_id=strategy_id, owner_id=current_user["user_id"])
    if not result:
        raise HTTPException(status_code=404, detail="策略不存在")
    return result


@router.put("/strategies/{strategy_id}")
def update_strategy(
    strategy_id: int, data: dict, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """更新策略"""
    service = TrafficStrategyService(db)
    result = service.update_strategy(strategy_id=strategy_id, owner_id=current_user["user_id"], data=data)
    if not result:
        raise HTTPException(status_code=404, detail="策略不存在")
    return result


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: int, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """删除策略"""
    service = TrafficStrategyService(db)
    success = service.delete_strategy(strategy_id=strategy_id, owner_id=current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {"message": "策略已删除"}


@router.put("/strategies/{strategy_id}/metrics")
def update_metrics(
    strategy_id: int, data: dict, current_user: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """更新策略效果指标"""
    service = TrafficStrategyService(db)
    metrics = data.get("metrics", {})
    result = service.update_metrics(strategy_id=strategy_id, owner_id=current_user["user_id"], metrics=metrics)
    if not result:
        raise HTTPException(status_code=404, detail="策略不存在")
    return result


@router.get("/summary")
def get_summary(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """获取引流效果汇总"""
    service = TrafficStrategyService(db)
    result = service.get_summary(owner_id=current_user["user_id"])
    return result
