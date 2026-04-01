"""
采集统计模块 - 记录和查询采集任务的统计数据。

功能：
- CollectMetrics 数据类：记录采集统计信息
- 统计持久化：支持写入数据库或日志
- 统计查询：支持按时间范围、平台等维度查询
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.models import CollectTask, MaterialItem
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class CollectMetrics:
    """采集任务统计数据结构。

    Attributes:
        task_id: 采集任务ID（可选）
        platform: 采集平台（如 xiaohongshu, douyin）
        keyword: 采集关键词
        success_count: 成功入库数量
        failed_count: 失败数量
        skipped_count: 跳过数量（断路器触发）
        duplicated_count: 去重数量
        elapsed_seconds: 耗时（秒）
        created_at: 记录创建时间
        metadata: 额外元数据
    """

    task_id: Optional[int] = None
    platform: str = ""
    keyword: str = ""
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duplicated_count: int = 0
    elapsed_seconds: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        """总处理数量"""
        return self.success_count + self.failed_count + self.skipped_count + self.duplicated_count

    @property
    def success_rate(self) -> float:
        """成功率（百分比）"""
        total = self.total_count
        if total == 0:
            return 0.0
        return round((self.success_count / total) * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data["total_count"] = self.total_count
        data["success_rate"] = self.success_rate
        return data

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        data = self.to_dict()
        # 处理 datetime 序列化
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        return json.dumps(data, ensure_ascii=False, default=str)


class CollectMetricsRecorder:
    """采集统计记录器"""

    @staticmethod
    def record_metrics(metrics: CollectMetrics, db: Optional[Session] = None) -> None:
        """
        记录采集统计信息。

        优先写入数据库（如果提供 db 会话），否则写入日志。

        Args:
            metrics: 采集统计对象
            db: 数据库会话（可选）
        """
        # 始终记录到日志
        logger.info(
            "Collect metrics recorded: task_id=%s, platform=%s, keyword=%s, "
            "success=%d, failed=%d, duplicated=%d, skipped=%d, "
            "total=%d, rate=%.2f%%, elapsed=%.2fs",
            metrics.task_id,
            metrics.platform,
            metrics.keyword,
            metrics.success_count,
            metrics.failed_count,
            metrics.duplicated_count,
            metrics.skipped_count,
            metrics.total_count,
            metrics.success_rate,
            metrics.elapsed_seconds,
        )

        # 如果提供了数据库会话，更新任务记录
        if db and metrics.task_id:
            try:
                CollectMetricsRecorder._update_task_metrics(db, metrics)
            except Exception as e:
                logger.error("Failed to update task metrics in database: %s", str(e))

    @staticmethod
    def _update_task_metrics(db: Session, metrics: CollectMetrics) -> None:
        """更新数据库中的任务统计信息"""
        task = db.query(CollectTask).filter(CollectTask.id == metrics.task_id).first()
        if task:
            # 更新任务统计字段（如果模型支持）
            if hasattr(task, "success_count"):
                task.success_count = metrics.success_count
            if hasattr(task, "failed_count"):
                task.failed_count = metrics.failed_count
            if hasattr(task, "duplicated_count"):
                task.duplicated_count = metrics.duplicated_count
            if hasattr(task, "elapsed_seconds"):
                task.elapsed_seconds = metrics.elapsed_seconds
            db.commit()

    @staticmethod
    def from_task_stats(
        task_id: Optional[int], platform: str, keyword: str, stats: dict[str, int], elapsed_seconds: float = 0.0
    ) -> CollectMetrics:
        """
        从任务统计字典创建 CollectMetrics 对象。

        Args:
            task_id: 任务ID
            platform: 平台
            keyword: 关键词
            stats: 统计字典（包含 inserted_count, failed_count 等）
            elapsed_seconds: 耗时

        Returns:
            CollectMetrics 对象
        """
        return CollectMetrics(
            task_id=task_id,
            platform=platform,
            keyword=keyword,
            success_count=stats.get("inserted_count", 0) + stats.get("review_count", 0),
            failed_count=stats.get("failed_count", 0),
            skipped_count=stats.get("skipped_count", 0),
            duplicated_count=stats.get("duplicate_count", 0),
            elapsed_seconds=elapsed_seconds,
        )


class CollectMetricsQuery:
    """采集统计查询器"""

    @staticmethod
    def get_recent_tasks_stats(
        db: Session, owner_id: int, days: int = 7, platform: Optional[str] = None
    ) -> dict[str, Any]:
        """
        获取近期采集任务统计。

        Args:
            db: 数据库会话
            owner_id: 用户ID
            days: 查询天数
            platform: 平台筛选（可选）

        Returns:
            统计数据字典
        """
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(CollectTask).filter(CollectTask.owner_id == owner_id, CollectTask.created_at >= start_date)

        if platform:
            query = query.filter(CollectTask.platform == platform)

        tasks = query.all()

        total_tasks = len(tasks)
        successful_tasks = sum(1 for t in tasks if t.status == "success")
        failed_tasks = sum(1 for t in tasks if t.status == "failed")

        # 汇总统计
        total_inserted = sum(t.inserted_count or 0 for t in tasks)
        total_failed = sum(t.failed_count or 0 for t in tasks)
        total_duplicate = sum(t.duplicate_count or 0 for t in tasks)

        # 按平台分组
        platform_stats = {}
        for t in tasks:
            p = t.platform or "unknown"
            if p not in platform_stats:
                platform_stats[p] = {"tasks": 0, "inserted": 0, "failed": 0}
            platform_stats[p]["tasks"] += 1
            platform_stats[p]["inserted"] += t.inserted_count or 0
            platform_stats[p]["failed"] += t.failed_count or 0

        # 计算平均成功率
        total_processed = total_inserted + total_failed + total_duplicate
        avg_success_rate = round((total_inserted / total_processed * 100), 2) if total_processed > 0 else 0.0

        return {
            "period_days": days,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "total_inserted": total_inserted,
            "total_failed": total_failed,
            "total_duplicate": total_duplicate,
            "avg_success_rate": avg_success_rate,
            "by_platform": platform_stats,
        }

    @staticmethod
    def get_overall_stats(db: Session, owner_id: int) -> dict[str, Any]:
        """
        获取整体采集统计。

        Args:
            db: 数据库会话
            owner_id: 用户ID

        Returns:
            统计数据字典
        """
        # 采集任务统计
        task_stats = (
            db.query(
                func.count(CollectTask.id).label("total"),
                func.sum(CollectTask.inserted_count).label("inserted"),
                func.sum(CollectTask.failed_count).label("failed"),
                func.sum(CollectTask.duplicate_count).label("duplicate"),
            )
            .filter(CollectTask.owner_id == owner_id)
            .first()
        )

        # 素材库统计
        material_stats = (
            db.query(func.count(MaterialItem.id).label("total"), func.sum(MaterialItem.like_count).label("total_likes"))
            .filter(MaterialItem.owner_id == owner_id)
            .first()
        )

        # 按平台统计
        platform_rows = (
            db.query(
                CollectTask.platform,
                func.count(CollectTask.id).label("task_count"),
                func.sum(CollectTask.inserted_count).label("inserted"),
            )
            .filter(CollectTask.owner_id == owner_id)
            .group_by(CollectTask.platform)
            .all()
        )

        return {
            "tasks": {
                "total": task_stats.total or 0,
                "inserted": task_stats.inserted or 0,
                "failed": task_stats.failed or 0,
                "duplicate": task_stats.duplicate or 0,
            },
            "materials": {"total": material_stats.total or 0, "total_likes": material_stats.total_likes or 0},
            "by_platform": {
                row.platform: {"tasks": row.task_count, "inserted": row.inserted or 0}
                for row in platform_rows
                if row.platform
            },
        }


# 便捷函数
def record_metrics(metrics: CollectMetrics, db: Optional[Session] = None) -> None:
    """记录采集统计的便捷函数"""
    CollectMetricsRecorder.record_metrics(metrics, db)


def get_recent_stats(db: Session, owner_id: int, days: int = 7, platform: Optional[str] = None) -> dict[str, Any]:
    """获取近期统计的便捷函数"""
    return CollectMetricsQuery.get_recent_tasks_stats(db, owner_id, days, platform)
