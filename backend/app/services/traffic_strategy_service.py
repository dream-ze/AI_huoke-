"""引流策略服务"""

import logging
from typing import List, Optional

from app.models.models import TrafficStrategy
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TrafficStrategyService:
    def __init__(self, db: Session):
        self.db = db

    def list_strategies(
        self,
        owner_id: int,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """策略列表"""
        q = self.db.query(TrafficStrategy).filter(TrafficStrategy.owner_id == owner_id)
        if platform:
            q = q.filter(TrafficStrategy.platform == platform)
        if status:
            q = q.filter(TrafficStrategy.status == status)
        total = q.count()
        items = q.order_by(desc(TrafficStrategy.created_at)).offset((page - 1) * page_size).limit(page_size).all()
        return {"total": total, "items": [self._to_dict(s) for s in items], "page": page, "page_size": page_size}

    def get_strategy(self, strategy_id: int, owner_id: int) -> Optional[dict]:
        """获取单个策略"""
        strategy = (
            self.db.query(TrafficStrategy)
            .filter(TrafficStrategy.id == strategy_id, TrafficStrategy.owner_id == owner_id)
            .first()
        )
        if strategy:
            return self._to_dict(strategy)
        return None

    def create_strategy(self, owner_id: int, data: dict) -> dict:
        """创建策略"""
        strategy = TrafficStrategy(
            owner_id=owner_id,
            name=data.get("name"),
            platform=data.get("platform"),
            strategy_type=data.get("strategy_type"),
            target_audience=data.get("target_audience"),
            cta_template=data.get("cta_template"),
            budget=data.get("budget"),
            performance_metrics=data.get("performance_metrics", {}),
            status=data.get("status", "active"),
            description=data.get("description"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        logger.info(f"Created traffic strategy {strategy.id} for owner {owner_id}")
        return self._to_dict(strategy)

    def update_strategy(self, strategy_id: int, owner_id: int, data: dict) -> Optional[dict]:
        """更新策略"""
        strategy = (
            self.db.query(TrafficStrategy)
            .filter(TrafficStrategy.id == strategy_id, TrafficStrategy.owner_id == owner_id)
            .first()
        )
        if not strategy:
            return None

        # 更新允许的字段
        allowed_fields = [
            "name",
            "platform",
            "strategy_type",
            "target_audience",
            "cta_template",
            "budget",
            "performance_metrics",
            "status",
            "description",
            "start_date",
            "end_date",
        ]
        for field in allowed_fields:
            if field in data:
                setattr(strategy, field, data[field])

        self.db.commit()
        self.db.refresh(strategy)
        logger.info(f"Updated traffic strategy {strategy_id} for owner {owner_id}")
        return self._to_dict(strategy)

    def delete_strategy(self, strategy_id: int, owner_id: int) -> bool:
        """删除策略"""
        strategy = (
            self.db.query(TrafficStrategy)
            .filter(TrafficStrategy.id == strategy_id, TrafficStrategy.owner_id == owner_id)
            .first()
        )
        if not strategy:
            return False

        self.db.delete(strategy)
        self.db.commit()
        logger.info(f"Deleted traffic strategy {strategy_id} for owner {owner_id}")
        return True

    def update_metrics(self, strategy_id: int, owner_id: int, metrics: dict) -> Optional[dict]:
        """更新效果指标"""
        strategy = (
            self.db.query(TrafficStrategy)
            .filter(TrafficStrategy.id == strategy_id, TrafficStrategy.owner_id == owner_id)
            .first()
        )
        if not strategy:
            return None

        current_metrics = strategy.performance_metrics or {}
        current_metrics.update(metrics)
        strategy.performance_metrics = current_metrics

        self.db.commit()
        self.db.refresh(strategy)
        logger.info(f"Updated metrics for traffic strategy {strategy_id}")
        return self._to_dict(strategy)

    def get_summary(self, owner_id: int) -> dict:
        """获取引流效果汇总"""
        # 按平台统计
        platform_stats = (
            self.db.query(
                TrafficStrategy.platform,
                func.count(TrafficStrategy.id).label("strategy_count"),
                func.sum(TrafficStrategy.budget).label("total_budget"),
            )
            .filter(TrafficStrategy.owner_id == owner_id)
            .group_by(TrafficStrategy.platform)
            .all()
        )

        # 按状态统计
        status_stats = (
            self.db.query(
                TrafficStrategy.status,
                func.count(TrafficStrategy.id).label("count"),
            )
            .filter(TrafficStrategy.owner_id == owner_id)
            .group_by(TrafficStrategy.status)
            .all()
        )

        # 总体统计
        total_stats = (
            self.db.query(
                func.count(TrafficStrategy.id).label("total_strategies"),
                func.sum(TrafficStrategy.budget).label("total_budget"),
            )
            .filter(TrafficStrategy.owner_id == owner_id)
            .first()
        )

        # 计算总效果指标
        all_strategies = self.db.query(TrafficStrategy).filter(TrafficStrategy.owner_id == owner_id).all()

        total_views = 0
        total_clicks = 0
        total_leads = 0
        total_conversions = 0

        for s in all_strategies:
            metrics = s.performance_metrics or {}
            total_views += metrics.get("views", 0) or 0
            total_clicks += metrics.get("clicks", 0) or 0
            total_leads += metrics.get("leads", 0) or 0
            total_conversions += metrics.get("conversions", 0) or 0

        cost_per_lead = (total_stats.total_budget or 0) / total_leads if total_leads > 0 else 0
        conversion_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0

        return {
            "total_strategies": total_stats.total_strategies or 0,
            "total_budget": float(total_stats.total_budget or 0),
            "by_platform": [
                {
                    "platform": p.platform,
                    "strategy_count": p.strategy_count,
                    "total_budget": float(p.total_budget or 0),
                }
                for p in platform_stats
            ],
            "by_status": [{"status": s.status, "count": s.count} for s in status_stats],
            "performance": {
                "total_views": total_views,
                "total_clicks": total_clicks,
                "total_leads": total_leads,
                "total_conversions": total_conversions,
                "cost_per_lead": round(cost_per_lead, 2),
                "conversion_rate": round(conversion_rate, 2),
            },
        }

    def _to_dict(self, strategy: TrafficStrategy) -> dict:
        """模型转字典"""
        return {
            "id": strategy.id,
            "owner_id": strategy.owner_id,
            "name": strategy.name,
            "platform": strategy.platform,
            "strategy_type": strategy.strategy_type,
            "target_audience": strategy.target_audience,
            "cta_template": strategy.cta_template,
            "budget": float(strategy.budget) if strategy.budget else None,
            "performance_metrics": strategy.performance_metrics or {},
            "status": strategy.status,
            "description": strategy.description,
            "start_date": strategy.start_date.isoformat() if strategy.start_date else None,
            "end_date": strategy.end_date.isoformat() if strategy.end_date else None,
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
        }
