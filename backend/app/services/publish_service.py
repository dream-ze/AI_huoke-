"""
发布管理服务层

提供发布任务管理、发布记录管理、发布统计分析等核心业务逻辑。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    Customer,
    Lead,
    PublishAccount,
    PublishedContent,
    PublishRecord,
    PublishTask,
    PublishTaskFeedback,
    RewrittenContent,
    User,
)
from fastapi import HTTPException, status
from sqlalchemy import Date, cast, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PublishService:
    """发布管理服务"""

    # ==================== 辅助方法 ====================

    @staticmethod
    def _get_task_or_404(db: Session, task_id: int) -> PublishTask:
        """获取任务，不存在则返回404"""
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish task not found")
        return task

    @staticmethod
    def _check_task_access(task: PublishTask, user_id: int) -> None:
        """检查用户是否有权限访问任务"""
        if task.owner_id != user_id and task.assigned_to != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this publish task")

    @staticmethod
    def _append_task_feedback(
        db: Session,
        task_id: int,
        action: str,
        user_id: int,
        note: str | None = None,
        payload: dict | None = None,
    ) -> PublishTaskFeedback:
        """添加任务反馈记录"""
        feedback = PublishTaskFeedback(
            task_id=task_id,
            action=action,
            note=note,
            payload=payload or {},
            created_by=user_id,
        )
        db.add(feedback)
        return feedback

    @staticmethod
    def _derive_lead_status(task: PublishTask) -> str:
        """根据任务指标推导线索状态"""
        if (task.conversions or 0) > 0:
            return "converted"
        if (task.valid_leads or 0) > 0:
            return "qualified"
        if (task.leads or 0) > 0 or (task.wechat_adds or 0) > 0:
            return "contacted"
        return "new"

    @staticmethod
    def _generate_tracking_code(platform: str, account_id: int, content_id: int) -> str:
        """生成追踪码

        格式: {platform}_{account_id}_{content_id}_{timestamp_hex}
        示例: xiaohongshu_123_456_18f3a2b9
        """
        timestamp_hex = hex(int(time.time()))[2:]  # 去掉 '0x' 前缀
        return f"{platform}_{account_id}_{content_id}_{timestamp_hex}"

    @staticmethod
    def _upsert_lead_from_task(db: Session, task: PublishTask) -> Lead:
        """根据发布任务创建或更新线索"""
        lead = db.query(Lead).filter(Lead.publish_task_id == task.id).first()
        owner_id = task.assigned_to or task.owner_id
        lead_status = PublishService._derive_lead_status(task)

        if lead is None:
            lead = Lead(
                owner_id=owner_id,
                publish_task_id=task.id,
                platform=task.platform,
                source="publish_task",
                title=task.task_title,
                post_url=task.post_url,
                wechat_adds=task.wechat_adds or 0,
                leads=task.leads or 0,
                valid_leads=task.valid_leads or 0,
                conversions=task.conversions or 0,
                status=lead_status,
                intention_level="medium",
                note="自动由发布任务回填生成/归并",
            )
            db.add(lead)
            db.flush()
        else:
            lead.owner_id = owner_id
            lead.platform = task.platform
            lead.title = task.task_title
            lead.post_url = task.post_url
            lead.wechat_adds = task.wechat_adds or 0
            lead.leads = task.leads or 0
            lead.valid_leads = task.valid_leads or 0
            lead.conversions = task.conversions or 0
            lead.status = lead_status

        customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
        if customer:
            customer.owner_id = lead.owner_id
            customer.customer_status = "converted" if lead.status == "converted" else customer.customer_status
        elif lead.conversions > 0:
            customer = Customer(
                owner_id=lead.owner_id,
                nickname=f"线索#{lead.id}",
                source_platform=lead.platform,
                source_content_id=task.rewritten_content_id,
                lead_id=lead.id,
                customer_status="converted",
                tags=["自动转客户", "来自发布任务"],
                intention_level="high",
                inquiry_content=f"由发布任务#{task.id}自动转化",
            )
            db.add(customer)

        return lead

    # ==================== 发布记录管理 ====================

    @staticmethod
    def create_publish_record(db: Session, record_data: dict) -> PublishRecord:
        """创建发布记录"""
        rewritten = (
            db.query(RewrittenContent).filter(RewrittenContent.id == record_data.get("rewritten_content_id")).first()
        )
        if not rewritten:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rewritten content not found")

        publish_record = PublishRecord(**record_data)
        db.add(publish_record)
        db.commit()
        db.refresh(publish_record)
        logger.info(f"Created publish record {publish_record.id} for content {record_data.get('rewritten_content_id')}")
        return publish_record

    @staticmethod
    def get_publish_record(db: Session, record_id: int) -> PublishRecord:
        """获取发布记录"""
        record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish record not found")
        return record

    @staticmethod
    def update_publish_record(db: Session, record_id: int, update_data: dict) -> PublishRecord:
        """更新发布记录指标"""
        record = PublishService.get_publish_record(db, record_id)
        for field, value in update_data.items():
            setattr(record, field, value)
        db.commit()
        db.refresh(record)
        logger.info(f"Updated publish record {record_id} with fields: {list(update_data.keys())}")
        return record

    @staticmethod
    def list_publish_records(
        db: Session,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PublishRecord]:
        """列出发布记录"""
        query = db.query(PublishRecord)
        if platform:
            query = query.filter(PublishRecord.platform == platform)
        return query.order_by(PublishRecord.publish_time.desc()).offset(skip).limit(limit).all()

    # ==================== 发布任务管理 ====================

    @staticmethod
    def create_publish_task(db: Session, task_data: dict, owner_id: int) -> PublishTask:
        """创建发布任务"""
        if task_data.get("rewritten_content_id") is not None:
            rewritten = (
                db.query(RewrittenContent).filter(RewrittenContent.id == task_data["rewritten_content_id"]).first()
            )
            if not rewritten:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rewritten content not found",
                )

        task = PublishTask(owner_id=owner_id, **task_data)
        db.add(task)
        db.flush()

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="create",
            user_id=owner_id,
            note="任务已创建",
        )
        db.commit()
        db.refresh(task)
        logger.info(f"Created publish task {task.id} by user {owner_id}")
        return task

    @staticmethod
    def get_publish_task(db: Session, task_id: int, user_id: int) -> PublishTask:
        """获取发布任务（带权限检查）"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)
        return task

    @staticmethod
    def get_publish_task_trace(db: Session, task_id: int, user_id: int) -> Dict[str, Any]:
        """获取发布任务的链路追踪信息"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        lead = db.query(Lead).filter(Lead.publish_task_id == task.id).first()
        customer = db.query(Customer).filter(Customer.lead_id == lead.id).first() if lead else None

        return {
            "task_id": task.id,
            "publish_record_id": task.publish_record_id,
            "lead_id": lead.id if lead else None,
            "customer_id": customer.id if customer else None,
        }

    @staticmethod
    def list_publish_tasks(
        db: Session,
        user_id: int,
        status_filter: Optional[str] = None,
        platform: Optional[str] = None,
        assigned_to: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PublishTask]:
        """列出用户相关的发布任务"""
        query = db.query(PublishTask).filter(
            or_(
                PublishTask.owner_id == user_id,
                PublishTask.assigned_to == user_id,
            )
        )

        if status_filter and status_filter != "all":
            query = query.filter(PublishTask.status == status_filter)
        if platform and platform != "all":
            query = query.filter(PublishTask.platform == platform)
        if assigned_to is not None:
            query = query.filter(PublishTask.assigned_to == assigned_to)

        return query.order_by(PublishTask.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: int,
        status: str,
        user_id: int,
        note: Optional[str] = None,
    ) -> PublishTask:
        """更新任务状态"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        task.status = status
        if note:
            PublishService._append_task_feedback(
                db,
                task_id=task.id,
                action=f"status_change_{status}",
                user_id=user_id,
                note=note,
            )
        db.commit()
        db.refresh(task)
        logger.info(f"Updated task {task_id} status to {status}")
        return task

    # ==================== 任务生命周期操作 ====================

    @staticmethod
    def claim_task(db: Session, task_id: int, user_id: int, note: Optional[str] = None) -> PublishTask:
        """认领任务"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        if task.status not in {"pending", "rejected"}:
            raise HTTPException(status_code=400, detail="Only pending/rejected tasks can be claimed")

        if task.assigned_to and task.assigned_to != user_id:
            raise HTTPException(status_code=400, detail="Task is assigned to another user")

        task.assigned_to = user_id
        task.status = "claimed"
        task.claimed_at = datetime.utcnow()

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="claim",
            user_id=user_id,
            note=note,
        )
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} claimed by user {user_id}")
        return task

    @staticmethod
    def assign_task(
        db: Session,
        task_id: int,
        assigned_to: int,
        user_id: int,
        note: Optional[str] = None,
    ) -> PublishTask:
        """分配任务给指定用户"""
        task = PublishService._get_task_or_404(db, task_id)

        if task.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Only task owner can assign task")

        if task.status in {"submitted", "closed"}:
            raise HTTPException(status_code=400, detail="Submitted/closed task cannot be re-assigned")

        assignee = db.query(User).filter(User.id == assigned_to, User.is_active.is_(True)).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee user not found or inactive")

        task.assigned_to = assigned_to
        task.status = "pending"
        task.claimed_at = None

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="assign",
            user_id=user_id,
            note=note,
            payload={"assigned_to": assigned_to},
        )
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} assigned to user {assigned_to} by {user_id}")
        return task

    @staticmethod
    def submit_publish(
        db: Session,
        task_id: int,
        submit_data: dict,
        user_id: int,
    ) -> PublishTask:
        """提交发布结果"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        if task.status in {"closed", "rejected"}:
            raise HTTPException(status_code=400, detail="Closed/rejected task cannot be submitted")

        if task.assigned_to and task.assigned_to != user_id:
            raise HTTPException(status_code=400, detail="Only assignee can submit this task")

        if task.assigned_to is None:
            task.assigned_to = user_id
            task.claimed_at = datetime.utcnow()

        note = submit_data.pop("note", None)
        posted_at = submit_data.get("posted_at") or datetime.utcnow()

        for field, value in submit_data.items():
            if value is not None:
                setattr(task, field, value)

        task.posted_at = posted_at
        task.status = "submitted"

        # 创建或更新发布记录
        if task.rewritten_content_id:
            if task.publish_record_id:
                record = db.query(PublishRecord).filter(PublishRecord.id == task.publish_record_id).first()
            else:
                record = PublishRecord(
                    rewritten_content_id=task.rewritten_content_id,
                    platform=task.platform,
                    account_name=task.account_name,
                    publish_time=posted_at,
                    published_by=str(user_id),
                )
                db.add(record)
                db.flush()
                task.publish_record_id = record.id

            if record:
                for field in (
                    "views",
                    "likes",
                    "comments",
                    "favorites",
                    "shares",
                    "private_messages",
                    "wechat_adds",
                    "leads",
                    "valid_leads",
                    "conversions",
                ):
                    setattr(record, field, getattr(task, field))
                record.publish_time = posted_at
                record.published_by = str(user_id)

        # 创建或更新 PublishedContent（带 tracking_code）
        publish_account_id = submit_data.get("publish_account_id")
        if publish_account_id:
            # 检查是否已存在该任务的 PublishedContent
            published_content = (
                db.query(PublishedContent)
                .filter(
                    PublishedContent.publish_account_id == publish_account_id,
                    PublishedContent.generation_result_id == task.rewritten_content_id,
                )
                .first()
            )

            if not published_content:
                # 生成唯一追踪码
                tracking_code = PublishService._generate_tracking_code(
                    task.platform, publish_account_id, task.rewritten_content_id or task.id
                )

                # 确保唯一性（如果冲突则重新生成）
                while db.query(PublishedContent).filter(PublishedContent.tracking_code == tracking_code).first():
                    tracking_code = PublishService._generate_tracking_code(
                        task.platform, publish_account_id, task.rewritten_content_id or task.id
                    )

                published_content = PublishedContent(
                    generation_result_id=task.rewritten_content_id,
                    publish_account_id=publish_account_id,
                    title=task.task_title,
                    content_text=task.content_text,
                    platform=task.platform,
                    publish_time=posted_at,
                    post_url=task.post_url,
                    views=task.views or 0,
                    likes=task.likes or 0,
                    comments=task.comments or 0,
                    shares=task.shares or 0,
                    wechat_adds=task.wechat_adds or 0,
                    leads_count=task.leads or 0,
                    tracking_code=tracking_code,
                )
                db.add(published_content)
                db.flush()
                logger.info(f"Created PublishedContent with tracking_code: {tracking_code}")

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="submit",
            user_id=user_id,
            note=note,
            payload=submit_data,
        )

        PublishService._upsert_lead_from_task(db, task)

        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} submitted by user {user_id}")
        return task

    @staticmethod
    def reject_task(db: Session, task_id: int, user_id: int, note: Optional[str] = None) -> PublishTask:
        """拒绝任务"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        if task.status == "closed":
            raise HTTPException(status_code=400, detail="Closed task cannot be rejected")

        task.status = "rejected"
        task.reject_reason = note

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="reject",
            user_id=user_id,
            note=note,
        )
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} rejected by user {user_id}")
        return task

    @staticmethod
    def close_task(db: Session, task_id: int, user_id: int, note: Optional[str] = None) -> PublishTask:
        """关闭任务"""
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        if task.status == "closed":
            return task

        task.status = "closed"
        task.close_reason = note
        task.closed_at = datetime.utcnow()

        PublishService._append_task_feedback(
            db,
            task_id=task.id,
            action="close",
            user_id=user_id,
            note=note,
        )
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} closed by user {user_id}")
        return task

    # ==================== 统计分析 ====================

    @staticmethod
    def get_task_stats(db: Session, user_id: int) -> Dict[str, int]:
        """获取用户任务状态统计"""
        rows = (
            db.query(PublishTask.status, func.count(PublishTask.id))
            .filter(
                or_(
                    PublishTask.owner_id == user_id,
                    PublishTask.assigned_to == user_id,
                )
            )
            .group_by(PublishTask.status)
            .all()
        )
        status_map = {key: count for key, count in rows if key}
        total = sum(status_map.values())
        return {
            "total": total,
            "pending": status_map.get("pending", 0),
            "claimed": status_map.get("claimed", 0),
            "submitted": status_map.get("submitted", 0),
            "rejected": status_map.get("rejected", 0),
            "closed": status_map.get("closed", 0),
        }

    @staticmethod
    def get_platform_stats(db: Session, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """获取平台发布统计"""
        since = datetime.utcnow() - timedelta(days=days)

        results = (
            db.query(
                PublishTask.platform,
                func.count(PublishTask.id).label("total_tasks"),
                func.sum(func.case([(PublishTask.status == "submitted", 1)], else_=0)).label("completed_tasks"),
                func.coalesce(func.sum(PublishTask.views), 0).label("total_views"),
                func.coalesce(func.sum(PublishTask.likes), 0).label("total_likes"),
                func.coalesce(func.sum(PublishTask.comments), 0).label("total_comments"),
                func.coalesce(func.sum(PublishTask.wechat_adds), 0).label("total_wechat_adds"),
                func.coalesce(func.sum(PublishTask.leads), 0).label("total_leads"),
                func.coalesce(func.sum(PublishTask.valid_leads), 0).label("total_valid_leads"),
                func.coalesce(func.sum(PublishTask.conversions), 0).label("total_conversions"),
            )
            .filter(
                or_(
                    PublishTask.owner_id == user_id,
                    PublishTask.assigned_to == user_id,
                ),
                PublishTask.created_at >= since,
            )
            .group_by(PublishTask.platform)
            .all()
        )

        response = []
        for row in results:
            total_tasks = row.total_tasks or 0
            completed_tasks = row.completed_tasks or 0
            total_views = row.total_views or 0
            total_conversions = row.total_conversions or 0

            avg_views = round(total_views / completed_tasks, 2) if completed_tasks > 0 else 0.0
            conversion_rate = round(total_conversions / completed_tasks * 100, 2) if completed_tasks > 0 else 0.0

            response.append(
                {
                    "platform": row.platform,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "total_views": total_views,
                    "total_likes": row.total_likes or 0,
                    "total_comments": row.total_comments or 0,
                    "total_wechat_adds": row.total_wechat_adds or 0,
                    "total_leads": row.total_leads or 0,
                    "total_valid_leads": row.total_valid_leads or 0,
                    "total_conversions": total_conversions,
                    "avg_views_per_task": avg_views,
                    "conversion_rate": conversion_rate,
                }
            )

        return response

    @staticmethod
    def get_roi_trend(db: Session, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """获取 ROI 趋势"""
        since = datetime.utcnow() - timedelta(days=days)

        results = (
            db.query(
                cast(PublishTask.posted_at, Date).label("date"),
                func.count(PublishTask.id).label("publish_count"),
                func.coalesce(func.sum(PublishTask.leads), 0).label("total_leads"),
                func.coalesce(func.sum(PublishTask.valid_leads), 0).label("total_valid_leads"),
                func.coalesce(func.sum(PublishTask.conversions), 0).label("total_conversions"),
            )
            .filter(
                or_(
                    PublishTask.owner_id == user_id,
                    PublishTask.assigned_to == user_id,
                ),
                PublishTask.posted_at >= since,
                PublishTask.posted_at.isnot(None),
            )
            .group_by(cast(PublishTask.posted_at, Date))
            .order_by(cast(PublishTask.posted_at, Date))
            .all()
        )

        response = []
        for row in results:
            publish_count = row.publish_count or 0
            total_leads = row.total_leads or 0
            total_conversions = row.total_conversions or 0

            lead_rate = round(total_leads / publish_count, 2) if publish_count > 0 else 0.0
            conversion_rate = round(total_conversions / publish_count, 2) if publish_count > 0 else 0.0

            response.append(
                {
                    "date": str(row.date) if row.date else "",
                    "publish_count": publish_count,
                    "total_leads": total_leads,
                    "total_valid_leads": row.total_valid_leads or 0,
                    "total_conversions": total_conversions,
                    "lead_rate": lead_rate,
                    "conversion_rate": conversion_rate,
                }
            )

        return response

    @staticmethod
    def get_content_analysis(db: Session, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """获取内容分析统计"""
        since = datetime.utcnow() - timedelta(days=days)

        results = (
            db.query(
                PublishTask.platform,
                func.count(PublishTask.id).label("task_count"),
                func.coalesce(func.avg(PublishTask.views), 0).label("avg_views"),
                func.coalesce(func.avg(PublishTask.likes), 0).label("avg_likes"),
                func.coalesce(func.avg(PublishTask.wechat_adds), 0).label("avg_wechat_adds"),
                func.coalesce(func.avg(PublishTask.conversions), 0).label("avg_conversions"),
            )
            .filter(
                or_(
                    PublishTask.owner_id == user_id,
                    PublishTask.assigned_to == user_id,
                ),
                PublishTask.created_at >= since,
                PublishTask.status == "submitted",
            )
            .group_by(PublishTask.platform)
            .all()
        )

        response = []
        for row in results:
            best_task = (
                db.query(PublishTask.task_title, PublishTask.conversions)
                .filter(
                    PublishTask.platform == row.platform,
                    or_(
                        PublishTask.owner_id == user_id,
                        PublishTask.assigned_to == user_id,
                    ),
                    PublishTask.created_at >= since,
                )
                .order_by(PublishTask.conversions.desc())
                .first()
            )

            response.append(
                {
                    "platform": row.platform,
                    "task_count": row.task_count or 0,
                    "avg_views": round(row.avg_views or 0, 2),
                    "avg_likes": round(row.avg_likes or 0, 2),
                    "avg_wechat_adds": round(row.avg_wechat_adds or 0, 2),
                    "avg_conversions": round(row.avg_conversions or 0, 2),
                    "best_task_title": best_task.task_title if best_task else None,
                    "best_task_conversions": best_task.conversions or 0 if best_task else 0,
                }
            )

        return response

    @staticmethod
    def get_account_stats(
        db: Session,
        account_name: str,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取发布账号统计"""
        query = db.query(PublishTask).filter(
            or_(
                PublishTask.owner_id == user_id,
                PublishTask.assigned_to == user_id,
            ),
            PublishTask.account_name == account_name,
        )

        if start_date:
            query = query.filter(PublishTask.created_at >= start_date)
        if end_date:
            query = query.filter(PublishTask.created_at <= end_date)

        tasks = query.all()

        if not tasks:
            return {
                "account_name": account_name,
                "total_tasks": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_wechat_adds": 0,
                "total_leads": 0,
                "total_valid_leads": 0,
                "total_conversions": 0,
                "avg_views": 0.0,
                "avg_likes": 0.0,
                "conversion_rate": 0.0,
            }

        total_views = sum(t.views or 0 for t in tasks)
        total_likes = sum(t.likes or 0 for t in tasks)
        total_comments = sum(t.comments or 0 for t in tasks)
        total_wechat_adds = sum(t.wechat_adds or 0 for t in tasks)
        total_leads = sum(t.leads or 0 for t in tasks)
        total_valid_leads = sum(t.valid_leads or 0 for t in tasks)
        total_conversions = sum(t.conversions or 0 for t in tasks)
        submitted_count = sum(1 for t in tasks if t.status == "submitted")

        return {
            "account_name": account_name,
            "total_tasks": len(tasks),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_wechat_adds": total_wechat_adds,
            "total_leads": total_leads,
            "total_valid_leads": total_valid_leads,
            "total_conversions": total_conversions,
            "avg_views": round(total_views / submitted_count, 2) if submitted_count > 0 else 0.0,
            "avg_likes": round(total_likes / submitted_count, 2) if submitted_count > 0 else 0.0,
            "conversion_rate": round(total_conversions / submitted_count * 100, 2) if submitted_count > 0 else 0.0,
        }

    # ==================== 发布效果相关 ====================

    @staticmethod
    def record_performance(db: Session, record_id: int, metrics: dict) -> PublishRecord:
        """记录发布效果指标"""
        record = PublishService.get_publish_record(db, record_id)

        for field in (
            "views",
            "likes",
            "comments",
            "favorites",
            "shares",
            "private_messages",
            "wechat_adds",
            "leads",
            "valid_leads",
            "conversions",
        ):
            if field in metrics:
                setattr(record, field, metrics[field])

        db.commit()
        db.refresh(record)
        logger.info(f"Recorded performance for publish record {record_id}")
        return record

    @staticmethod
    def get_content_performance(db: Session, content_id: int, user_id: int) -> Dict[str, Any]:
        """获取单条内容的发布效果"""
        tasks = (
            db.query(PublishTask)
            .filter(
                PublishTask.rewritten_content_id == content_id,
                or_(
                    PublishTask.owner_id == user_id,
                    PublishTask.assigned_to == user_id,
                ),
            )
            .all()
        )

        if not tasks:
            return {
                "content_id": content_id,
                "total_publishes": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_wechat_adds": 0,
                "total_leads": 0,
                "total_valid_leads": 0,
                "total_conversions": 0,
                "platforms": [],
            }

        total_views = sum(t.views or 0 for t in tasks)
        total_likes = sum(t.likes or 0 for t in tasks)
        total_comments = sum(t.comments or 0 for t in tasks)
        total_wechat_adds = sum(t.wechat_adds or 0 for t in tasks)
        total_leads = sum(t.leads or 0 for t in tasks)
        total_valid_leads = sum(t.valid_leads or 0 for t in tasks)
        total_conversions = sum(t.conversions or 0 for t in tasks)

        platforms = {}
        for task in tasks:
            if task.platform not in platforms:
                platforms[task.platform] = {
                    "platform": task.platform,
                    "publish_count": 0,
                    "views": 0,
                    "likes": 0,
                    "conversions": 0,
                }
            platforms[task.platform]["publish_count"] += 1
            platforms[task.platform]["views"] += task.views or 0
            platforms[task.platform]["likes"] += task.likes or 0
            platforms[task.platform]["conversions"] += task.conversions or 0

        return {
            "content_id": content_id,
            "total_publishes": len(tasks),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_wechat_adds": total_wechat_adds,
            "total_leads": total_leads,
            "total_valid_leads": total_valid_leads,
            "total_conversions": total_conversions,
            "platforms": list(platforms.values()),
        }

    # ==================== 活动关联 ====================

    @staticmethod
    def link_to_campaign(db: Session, task_id: int, campaign_id: int, user_id: int) -> PublishTask:
        """关联发布内容到获客活动

        注意：当前 PublishTask 模型没有 campaign_id 字段。
        此方法为预留扩展接口，需要后续数据库迁移添加字段后实现。
        """
        task = PublishService._get_task_or_404(db, task_id)
        PublishService._check_task_access(task, user_id)

        # TODO: 等待 PublishTask 模型添加 campaign_id 字段后实现
        # task.campaign_id = campaign_id
        # db.commit()
        # db.refresh(task)

        logger.warning(f"link_to_campaign called but campaign_id field not yet implemented on PublishTask")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Campaign linking not yet implemented - awaiting database migration",
        )

    # ==================== CSV 导出 ====================

    @staticmethod
    def export_tasks_csv(
        db: Session,
        user_id: int,
        status_filter: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """导出任务数据为 CSV 格式"""
        query = db.query(PublishTask).filter(
            or_(
                PublishTask.owner_id == user_id,
                PublishTask.assigned_to == user_id,
            )
        )

        if status_filter and status_filter != "all":
            query = query.filter(PublishTask.status == status_filter)
        if platform and platform != "all":
            query = query.filter(PublishTask.platform == platform)

        tasks = query.order_by(PublishTask.created_at.desc()).limit(5000).all()

        return [
            {
                "id": t.id,
                "platform": t.platform,
                "account_name": t.account_name,
                "task_title": t.task_title,
                "status": t.status,
                "assigned_to": t.assigned_to or "",
                "post_url": t.post_url or "",
                "wechat_adds": t.wechat_adds or 0,
                "leads": t.leads or 0,
                "valid_leads": t.valid_leads or 0,
                "conversions": t.conversions or 0,
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "updated_at": t.updated_at.isoformat() if t.updated_at else "",
            }
            for t in tasks
        ]

    # ==================== 追踪码与线索关联 ====================

    @staticmethod
    def get_content_by_tracking_code(db: Session, tracking_code: str) -> Optional[PublishedContent]:
        """通过追踪码查询发布内容"""
        return db.query(PublishedContent).filter(PublishedContent.tracking_code == tracking_code).first()

    @staticmethod
    def get_content_with_leads_by_tracking_code(db: Session, tracking_code: str) -> Optional[Dict[str, Any]]:
        """通过追踪码查询发布内容及关联线索"""
        content = db.query(PublishedContent).filter(PublishedContent.tracking_code == tracking_code).first()

        if not content:
            return None

        # 查询关联的线索
        leads = db.query(Lead).filter(Lead.published_content_id == content.id).all()

        # 查询关联的发布账号
        account = None
        if content.publish_account_id:
            account = db.query(PublishAccount).filter(PublishAccount.id == content.publish_account_id).first()

        return {
            "content": {
                "id": content.id,
                "tracking_code": content.tracking_code,
                "title": content.title,
                "platform": content.platform,
                "content_text": content.content_text,
                "publish_time": content.publish_time.isoformat() if content.publish_time else None,
                "post_url": content.post_url,
                "views": content.views or 0,
                "likes": content.likes or 0,
                "comments": content.comments or 0,
                "shares": content.shares or 0,
                "wechat_adds": content.wechat_adds or 0,
                "leads_count": content.leads_count or 0,
            },
            "account": (
                {
                    "id": account.id,
                    "account_name": account.account_name,
                    "platform": account.platform,
                }
                if account
                else None
            ),
            "leads": [
                {
                    "id": lead.id,
                    "title": lead.title,
                    "status": lead.status,
                    "wechat_adds": lead.wechat_adds or 0,
                    "leads": lead.leads or 0,
                    "valid_leads": lead.valid_leads or 0,
                    "conversions": lead.conversions or 0,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                }
                for lead in leads
            ],
        }

    @staticmethod
    def get_account_lead_stats(
        db: Session,
        account_id: int,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """获取账号维度的线索统计

        Args:
            db: 数据库会话
            account_id: 发布账号ID
            date_range: 日期范围 (start_date, end_date)

        Returns:
            账号线索统计信息
        """
        # 获取账号信息
        account = db.query(PublishAccount).filter(PublishAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish account not found")

        # 构建查询条件
        filters = [Lead.publish_account_id == account_id]
        if date_range:
            start_date, end_date = date_range
            filters.append(Lead.created_at >= start_date)
            filters.append(Lead.created_at <= end_date)

        # 统计线索数据
        stats = (
            db.query(
                func.count(Lead.id).label("total_leads"),
                func.sum(Lead.leads).label("total_lead_count"),
                func.sum(Lead.valid_leads).label("total_valid_leads"),
                func.sum(Lead.conversions).label("total_conversions"),
                func.sum(Lead.wechat_adds).label("total_wechat_adds"),
            )
            .filter(*filters)
            .first()
        )

        # 按状态分组统计
        status_stats = (
            db.query(
                Lead.status,
                func.count(Lead.id).label("count"),
            )
            .filter(*filters)
            .group_by(Lead.status)
            .all()
        )

        status_distribution = {row.status: row.count for row in status_stats}

        # 获取该账号关联的内容列表
        contents = db.query(PublishedContent).filter(PublishedContent.publish_account_id == account_id).all()

        content_stats = []
        for content in contents:
            content_leads = db.query(Lead).filter(Lead.published_content_id == content.id).all()
            content_stats.append(
                {
                    "content_id": content.id,
                    "title": content.title,
                    "tracking_code": content.tracking_code,
                    "publish_time": content.publish_time.isoformat() if content.publish_time else None,
                    "leads_count": len(content_leads),
                    "conversions": sum(lead.conversions or 0 for lead in content_leads),
                }
            )

        total_leads = stats.total_leads or 0
        total_conversions = stats.total_conversions or 0

        return {
            "account_id": account_id,
            "account_name": account.account_name,
            "platform": account.platform,
            "date_range": {
                "start": date_range[0].isoformat() if date_range else None,
                "end": date_range[1].isoformat() if date_range else None,
            },
            "total_leads": total_leads,
            "total_lead_count": stats.total_lead_count or 0,
            "total_valid_leads": stats.total_valid_leads or 0,
            "total_conversions": total_conversions,
            "total_wechat_adds": stats.total_wechat_adds or 0,
            "conversion_rate": round(total_conversions / total_leads, 4) if total_leads > 0 else 0.0,
            "status_distribution": status_distribution,
            "contents": sorted(content_stats, key=lambda x: x["leads_count"], reverse=True),
        }

    @staticmethod
    def get_content_lead_stats(db: Session, content_id: int) -> Dict[str, Any]:
        """获取内容维度的线索统计

        Args:
            db: 数据库会话
            content_id: 发布内容ID

        Returns:
            内容线索统计信息
        """
        content = db.query(PublishedContent).filter(PublishedContent.id == content_id).first()
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Published content not found")

        # 查询关联线索
        leads = db.query(Lead).filter(Lead.published_content_id == content_id).all()

        # 统计
        total_leads = len(leads)
        total_wechat_adds = sum(lead.wechat_adds or 0 for lead in leads)
        total_lead_count = sum(lead.leads or 0 for lead in leads)
        total_valid_leads = sum(lead.valid_leads or 0 for lead in leads)
        total_conversions = sum(lead.conversions or 0 for lead in leads)

        # 按状态分组
        status_distribution = {}
        for lead in leads:
            status_distribution[lead.status] = status_distribution.get(lead.status, 0) + 1

        # 查询关联账号
        account = None
        if content.publish_account_id:
            account = db.query(PublishAccount).filter(PublishAccount.id == content.publish_account_id).first()

        return {
            "content_id": content_id,
            "tracking_code": content.tracking_code,
            "title": content.title,
            "platform": content.platform,
            "publish_time": content.publish_time.isoformat() if content.publish_time else None,
            "post_url": content.post_url,
            "total_leads": total_leads,
            "total_lead_count": total_lead_count,
            "total_valid_leads": total_valid_leads,
            "total_conversions": total_conversions,
            "total_wechat_adds": total_wechat_adds,
            "conversion_rate": round(total_conversions / total_leads, 4) if total_leads > 0 else 0.0,
            "status_distribution": status_distribution,
            "account": (
                {
                    "id": account.id,
                    "account_name": account.account_name,
                    "platform": account.platform,
                }
                if account
                else None
            ),
            "leads": [
                {
                    "id": lead.id,
                    "title": lead.title,
                    "status": lead.status,
                    "wechat_adds": lead.wechat_adds or 0,
                    "leads": lead.leads or 0,
                    "valid_leads": lead.valid_leads or 0,
                    "conversions": lead.conversions or 0,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                }
                for lead in leads
            ],
        }
