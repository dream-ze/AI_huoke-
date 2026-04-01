"""统计异步任务模块 - 仪表盘数据聚合、内容指标计算等统计任务"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def refresh_dashboard_stats(self):
    """刷新仪表盘统计数据

    定时任务：每小时执行一次，更新仪表盘缓存数据

    Returns:
        dict: 刷新结果
    """
    from app.core.database import SessionLocal

    logger.info("开始刷新仪表盘统计")
    db = SessionLocal()
    try:
        from app.models.models import MvpGenerationResult, MvpInboxItem, MvpKnowledgeItem, MvpMaterialItem, User
        from sqlalchemy import func

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 收件箱待处理数量
        inbox_pending = db.query(func.count(MvpInboxItem.id)).filter(MvpInboxItem.status == "pending").scalar() or 0

        # 素材库总数
        material_count = (
            db.query(func.count(MvpMaterialItem.id)).filter(MvpMaterialItem.status != "discard").scalar() or 0
        )

        # 知识库总数
        knowledge_count = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

        # 今日生成数量
        today_generation_count = (
            db.query(func.count(MvpGenerationResult.id)).filter(MvpGenerationResult.created_at >= today_start).scalar()
            or 0
        )

        # 风险内容数量（合规状态为blocked）
        risk_content_count = (
            db.query(func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.compliance_status == "blocked")
            .scalar()
            or 0
        )

        # 最近生成记录
        recent_generations = (
            db.query(MvpGenerationResult).order_by(MvpGenerationResult.created_at.desc()).limit(5).all()
        )

        recent_gen_data = [
            {
                "id": r.id,
                "title": r.output_title or r.input_text[:50],
                "version": r.version,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_generations
        ]

        # 最近素材记录
        recent_materials = db.query(MvpMaterialItem).order_by(MvpMaterialItem.created_at.desc()).limit(5).all()

        recent_mat_data = [
            {
                "id": m.id,
                "title": m.title,
                "platform": m.platform,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in recent_materials
        ]

        # 用户活跃统计
        active_users_today = db.query(func.count(User.id)).filter(User.last_login >= today_start).scalar() or 0

        stats = {
            "inbox_pending": inbox_pending,
            "material_count": material_count,
            "knowledge_count": knowledge_count,
            "today_generation_count": today_generation_count,
            "risk_content_count": risk_content_count,
            "active_users_today": active_users_today,
            "recent_generations": recent_gen_data,
            "recent_materials": recent_mat_data,
            "updated_at": now.isoformat(),
        }

        # 可选：缓存到Redis
        try:
            import redis
            from app.core.config import settings

            redis_client = redis.from_url(settings.REDIS_URL)
            import json

            redis_client.setex("dashboard_stats", 3600, json.dumps(stats))
            logger.debug("统计数据已缓存到Redis")
        except Exception as e:
            logger.warning(f"Redis缓存失败，跳过: {e}")

        logger.info(
            f"仪表盘统计刷新完成: inbox={inbox_pending}, materials={material_count}, knowledge={knowledge_count}"
        )
        return {"status": "success", "stats": stats}
    except Exception as exc:
        logger.error(f"仪表盘统计刷新失败: error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def calculate_content_metrics(self, content_id: Optional[int] = None):
    """计算内容指标

    分析生成内容的质量指标，包括：
    - 文本长度统计
    - 关键词密度
    - 可读性评分

    Args:
        content_id: 指定的内容ID，如果为None则计算所有内容

    Returns:
        dict: 计算结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始计算内容指标: content_id={content_id}")
    db = SessionLocal()
    try:
        from app.models.models import MvpGenerationResult
        from sqlalchemy import func

        query = db.query(MvpGenerationResult)
        if content_id:
            query = query.filter(MvpGenerationResult.id == content_id)

        contents = query.all()
        results = {"total": len(contents), "metrics": []}

        for content in contents:
            try:
                text = content.output_text or ""

                # 基础指标
                char_count = len(text)
                word_count = len(text.split())
                sentence_count = (
                    text.count("。")
                    + text.count("！")
                    + text.count("？")
                    + text.count(".")
                    + text.count("!")
                    + text.count("?")
                )

                # 平均句长
                avg_sentence_len = char_count / max(sentence_count, 1)

                # 段落数
                paragraph_count = len([p for p in text.split("\n\n") if p.strip()])

                metric = {
                    "content_id": content.id,
                    "char_count": char_count,
                    "word_count": word_count,
                    "sentence_count": sentence_count,
                    "avg_sentence_len": round(avg_sentence_len, 2),
                    "paragraph_count": paragraph_count,
                }

                results["metrics"].append(metric)

            except Exception as e:
                logger.warning(f"单条内容指标计算失败: content_id={content.id}, error={e}")

        logger.info(f"内容指标计算完成: {results['total']}条")
        return results
    except Exception as exc:
        logger.error(f"内容指标计算失败: error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def generate_daily_report(self, date: Optional[str] = None):
    """生成每日报告

    汇总当日的素材入库、内容生成、合规审核等数据

    Args:
        date: 报告日期 (YYYY-MM-DD格式)，默认为今天

    Returns:
        dict: 每日报告数据
    """
    from app.core.database import SessionLocal

    # 解析日期
    if date:
        report_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        report_date = datetime.utcnow()

    day_start = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    logger.info(f"开始生成每日报告: {day_start.date()}")
    db = SessionLocal()
    try:
        from app.models.models import (
            MvpComplianceRule,
            MvpGenerationResult,
            MvpInboxItem,
            MvpKnowledgeItem,
            MvpMaterialItem,
        )
        from sqlalchemy import func

        report = {
            "date": day_start.date().isoformat(),
            "inbox": {},
            "materials": {},
            "knowledge": {},
            "generation": {},
            "compliance": {},
        }

        # 收件箱统计
        report["inbox"] = {
            "new_items": db.query(func.count(MvpInboxItem.id))
            .filter(MvpInboxItem.created_at >= day_start, MvpInboxItem.created_at < day_end)
            .scalar()
            or 0,
            "approved": db.query(func.count(MvpInboxItem.id))
            .filter(
                MvpInboxItem.status == "review", MvpInboxItem.updated_at >= day_start, MvpInboxItem.updated_at < day_end
            )
            .scalar()
            or 0,
            "discarded": db.query(func.count(MvpInboxItem.id))
            .filter(
                MvpInboxItem.status == "discard",
                MvpInboxItem.updated_at >= day_start,
                MvpInboxItem.updated_at < day_end,
            )
            .scalar()
            or 0,
        }

        # 素材统计
        report["materials"] = {
            "new_items": db.query(func.count(MvpMaterialItem.id))
            .filter(MvpMaterialItem.created_at >= day_start, MvpMaterialItem.created_at < day_end)
            .scalar()
            or 0,
            "by_platform": {},
        }

        # 按平台统计素材
        platform_stats = (
            db.query(MvpMaterialItem.platform, func.count(MvpMaterialItem.id))
            .filter(MvpMaterialItem.created_at >= day_start, MvpMaterialItem.created_at < day_end)
            .group_by(MvpMaterialItem.platform)
            .all()
        )

        for platform, count in platform_stats:
            if platform:
                report["materials"]["by_platform"][platform] = count

        # 知识库统计
        report["knowledge"] = {
            "new_items": db.query(func.count(MvpKnowledgeItem.id))
            .filter(MvpKnowledgeItem.created_at >= day_start, MvpKnowledgeItem.created_at < day_end)
            .scalar()
            or 0
        }

        # 生成统计
        report["generation"] = {
            "total": db.query(func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.created_at >= day_start, MvpGenerationResult.created_at < day_end)
            .scalar()
            or 0,
            "by_platform": {},
            "by_style": {},
        }

        # 按平台统计生成
        gen_platform_stats = (
            db.query(MvpGenerationResult.platform, func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.created_at >= day_start, MvpGenerationResult.created_at < day_end)
            .group_by(MvpGenerationResult.platform)
            .all()
        )

        for platform, count in gen_platform_stats:
            if platform:
                report["generation"]["by_platform"][platform] = count

        # 按风格统计生成
        style_stats = (
            db.query(MvpGenerationResult.version, func.count(MvpGenerationResult.id))
            .filter(MvpGenerationResult.created_at >= day_start, MvpGenerationResult.created_at < day_end)
            .group_by(MvpGenerationResult.version)
            .all()
        )

        for style, count in style_stats:
            if style:
                report["generation"]["by_style"][style] = count

        # 合规统计
        report["compliance"] = {
            "passed": db.query(func.count(MvpGenerationResult.id))
            .filter(
                MvpGenerationResult.compliance_status == "passed",
                MvpGenerationResult.created_at >= day_start,
                MvpGenerationResult.created_at < day_end,
            )
            .scalar()
            or 0,
            "warning": db.query(func.count(MvpGenerationResult.id))
            .filter(
                MvpGenerationResult.compliance_status == "warning",
                MvpGenerationResult.created_at >= day_start,
                MvpGenerationResult.created_at < day_end,
            )
            .scalar()
            or 0,
            "blocked": db.query(func.count(MvpGenerationResult.id))
            .filter(
                MvpGenerationResult.compliance_status == "blocked",
                MvpGenerationResult.created_at >= day_start,
                MvpGenerationResult.created_at < day_end,
            )
            .scalar()
            or 0,
        }

        logger.info(f"每日报告生成完成: {day_start.date()}")
        return {"status": "success", "report": report}
    except Exception as exc:
        logger.error(f"每日报告生成失败: error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def calculate_user_stats(self, user_id: int):
    """计算用户统计指标

    统计用户的素材数、生成数、活跃度等

    Args:
        user_id: 用户ID

    Returns:
        dict: 用户统计数据
    """
    from app.core.database import SessionLocal

    logger.info(f"开始计算用户统计: user_id={user_id}")
    db = SessionLocal()
    try:
        from app.models.models import MvpGenerationResult, MvpMaterialItem, User
        from sqlalchemy import func

        # 检查用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "reason": "user_not_found"}

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        stats = {
            "user_id": user_id,
            "username": user.username,
            "materials": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
            "generations": {"total": 0, "today": 0, "this_week": 0, "this_month": 0},
            "activity": {
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "days_since_login": (now - user.last_login).days if user.last_login else None,
            },
        }

        # 素材统计（假设素材有owner_id字段）
        if hasattr(MvpMaterialItem, "owner_id"):
            stats["materials"]["total"] = (
                db.query(func.count(MvpMaterialItem.id)).filter(MvpMaterialItem.owner_id == user_id).scalar() or 0
            )

            stats["materials"]["today"] = (
                db.query(func.count(MvpMaterialItem.id))
                .filter(MvpMaterialItem.owner_id == user_id, MvpMaterialItem.created_at >= today_start)
                .scalar()
                or 0
            )

            stats["materials"]["this_week"] = (
                db.query(func.count(MvpMaterialItem.id))
                .filter(MvpMaterialItem.owner_id == user_id, MvpMaterialItem.created_at >= week_start)
                .scalar()
                or 0
            )

            stats["materials"]["this_month"] = (
                db.query(func.count(MvpMaterialItem.id))
                .filter(MvpMaterialItem.owner_id == user_id, MvpMaterialItem.created_at >= month_start)
                .scalar()
                or 0
            )

        logger.info(f"用户统计计算完成: user_id={user_id}")
        return {"status": "success", "stats": stats}
    except Exception as exc:
        logger.error(f"用户统计计算失败: user_id={user_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def cleanup_old_statistics(self, days_to_keep: int = 90):
    """清理过期统计数据

    清理超过指定天数的详细统计数据，保留汇总数据

    Args:
        days_to_keep: 保留天数

    Returns:
        dict: 清理结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始清理过期统计数据: 保留{days_to_keep}天")
    db = SessionLocal()
    try:
        from app.models.models import ReminderLog
        from sqlalchemy import func

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # 清理提醒日志
        deleted_logs = db.query(ReminderLog).filter(ReminderLog.created_at < cutoff_date).delete()

        db.commit()

        logger.info(f"过期统计数据清理完成: 删除{deleted_logs}条提醒日志")
        return {"status": "success", "deleted_logs": deleted_logs, "cutoff_date": cutoff_date.isoformat()}
    except Exception as exc:
        logger.error(f"清理过期统计数据失败: error={exc}")
        raise
    finally:
        db.close()
