"""Celery 异步任务应用配置"""

from app.core.config import settings
from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "zhihuokeke",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 序列化配置
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务超时配置
    task_time_limit=300,  # 5分钟硬超时
    task_soft_time_limit=280,  # 4分40秒软超时
    task_acks_late=True,  # 任务完成后确认
    task_reject_on_worker_lost=True,  # 防止任务丢失
    result_expires=3600,  # 结果保留1小时
    task_track_started=True,  # 跟踪任务开始
    # 任务路由配置（可选）
    task_routes={
        "app.tasks.ai_tasks.*": {"queue": "ai"},
        "app.tasks.material_tasks.*": {"queue": "material"},
        "app.tasks.stats_tasks.*": {"queue": "stats"},
        "app.tasks.wecom_tasks.*": {"queue": "wecom"},
    },
)

# 定时任务调度
celery.conf.beat_schedule = {
    # 提醒任务
    "daily-follow-summary": {
        "task": "app.tasks.reminder_tasks.run_daily_summary_tasks",
        "schedule": crontab(hour=9, minute=0),  # 每天早上9点
    },
    "hourly-urgent-check": {
        "task": "app.tasks.reminder_tasks.run_reminder_tasks",
        "schedule": crontab(minute=0),  # 每小时整点
    },
    # 统计任务
    "refresh-dashboard-stats": {
        "task": "app.tasks.stats_tasks.refresh_dashboard_stats",
        "schedule": crontab(minute=0),  # 每小时刷新仪表盘统计
    },
    "generate-daily-report": {
        "task": "app.tasks.stats_tasks.generate_daily_report",
        "schedule": crontab(hour=23, minute=30),  # 每天23:30生成日报
    },
    # 清理任务
    "cleanup-old-statistics": {
        "task": "app.tasks.stats_tasks.cleanup_old_statistics",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点清理
    },
}

# 自动发现任务模块
# autodiscover_tasks 会自动发现 app/tasks/ 目录下所有模块的任务
celery.autodiscover_tasks(
    [
        "app.tasks.reminder_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.material_tasks",
        "app.tasks.stats_tasks",
        "app.tasks.wecom_tasks",
    ]
)
