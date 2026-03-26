from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import CollectTask, ContentAsset, EmployeeLinkSubmission, MaterialInbox
from app.models.models import InsightTopic
from app.services.collector.browser_collector_client import BrowserCollectorClient
from app.services.insight_service import InsightService


class AcquisitionIntakeService:
    """Core intake workflows: keyword task and employee/wechat link intake."""

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            text = value.strip().replace("Z", "+00:00")
            if not text:
                return None
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _ingest_items(
        db: Session,
        owner_id: int,
        source_channel: str,
        items: list[dict[str, Any]],
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> int:
        count = 0
        for item in items:
            inbox = MaterialInbox(
                owner_id=owner_id,
                source_channel=source_channel,
                source_task_id=source_task_id,
                source_submission_id=source_submission_id,
                platform=str(item.get("platform") or "other"),
                title=item.get("title"),
                author=item.get("author"),
                content=item.get("content"),
                url=item.get("url"),
                cover_url=item.get("cover_url"),
                like_count=AcquisitionIntakeService._to_int(item.get("like_count")),
                comment_count=AcquisitionIntakeService._to_int(item.get("comment_count")),
                collect_count=AcquisitionIntakeService._to_int(item.get("collect_count")),
                share_count=AcquisitionIntakeService._to_int(item.get("share_count")),
                publish_time=AcquisitionIntakeService._to_datetime(item.get("publish_time")),
                raw_data=item.get("raw_data") or item,
                status="pending",
                submitted_by_employee_id=submitted_by_employee_id,
                remark=remark,
            )
            db.add(inbox)
            count += 1
        db.flush()
        return count

    @staticmethod
    def create_keyword_task(
        db: Session,
        owner_id: int,
        platform: str,
        keyword: str,
        max_items: int,
        client: Optional[BrowserCollectorClient] = None,
    ) -> dict[str, Any]:
        collector_client = client or BrowserCollectorClient()
        task = CollectTask(
            owner_id=owner_id,
            task_type="keyword",
            platform=platform,
            keyword=keyword,
            max_items=max_items,
            status="pending",
        )
        db.add(task)
        db.flush()
        task_id = int(getattr(task, "id"))

        try:
            result = collector_client.collect_keyword(platform=platform, keyword=keyword, max_items=max_items)
            rows = result.get("items") or []
            inbox_count = AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel="collect_task",
                items=rows,
                source_task_id=task_id,
            )
            setattr(task, "result_count", int(result.get("total") or len(rows)))
            setattr(task, "status", "success")
            db.commit()
            db.refresh(task)
            return {
                "task_id": task_id,
                "status": getattr(task, "status"),
                "result_count": int(getattr(task, "result_count")),
                "inbox_count": inbox_count,
            }
        except Exception as exc:
            setattr(task, "status", "failed")
            setattr(task, "error_message", str(exc))
            db.commit()
            raise

    @staticmethod
    def submit_link(
        db: Session,
        owner_id: int,
        employee_id: Optional[int],
        url: str,
        note: Optional[str],
        source_type: str = "manual_link",
        client: Optional[BrowserCollectorClient] = None,
    ) -> dict[str, Any]:
        collector_client = client or BrowserCollectorClient()
        submission = EmployeeLinkSubmission(
            owner_id=owner_id,
            employee_id=employee_id,
            source_type=source_type,
            url=url,
            note=note,
            status="pending",
        )
        db.add(submission)
        db.flush()
        submission_id = int(getattr(submission, "id"))

        try:
            result = collector_client.collect_single_link(url=url)
            rows = result.get("items") or []
            if not rows:
                raise ValueError("采集服务未返回可入库内容")

            row = rows[0]
            setattr(submission, "platform", str(row.get("platform") or getattr(submission, "platform") or "other"))
            channel = "wechat_robot" if source_type == "wechat_robot" else "employee_submission"
            AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel=channel,
                items=[row],
                source_submission_id=submission_id,
                submitted_by_employee_id=employee_id,
                remark=note,
            )
            setattr(submission, "status", "success")
            db.commit()
            return {
                "submission_id": submission_id,
                "status": getattr(submission, "status"),
                "platform": getattr(submission, "platform"),
            }
        except Exception as exc:
            setattr(submission, "status", "failed")
            setattr(submission, "error_message", str(exc))
            db.commit()
            raise

    @staticmethod
    def list_inbox(
        db: Session,
        owner_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        source_channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MaterialInbox]:
        query = db.query(MaterialInbox).filter(MaterialInbox.owner_id == owner_id)
        if status:
            query = query.filter(MaterialInbox.status == status)
        if platform:
            query = query.filter(MaterialInbox.platform == platform)
        if source_channel:
            query = query.filter(MaterialInbox.source_channel == source_channel)
        return query.order_by(MaterialInbox.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_inbox_item(db: Session, owner_id: int, inbox_id: int) -> Optional[MaterialInbox]:
        return (
            db.query(MaterialInbox)
            .filter(MaterialInbox.owner_id == owner_id, MaterialInbox.id == inbox_id)
            .first()
        )

    # ─────────────────────────────────────────
    # 收件箱分拣动作
    # ─────────────────────────────────────────

    @staticmethod
    def _get_pending_item(db: Session, owner_id: int, inbox_id: int) -> MaterialInbox:
        item = AcquisitionIntakeService.get_inbox_item(db, owner_id, inbox_id)
        if item is None:
            raise ValueError("收件箱内容不存在")
        if str(getattr(item, "status")) != "pending":
            raise ValueError(f"当前状态为 {getattr(item, 'status')}，只有 pending 状态允许操作")
        return item

    @staticmethod
    def _build_content_asset(db: Session, owner_id: int, item: MaterialInbox, remark: Optional[str]) -> int:
        asset = ContentAsset(
            owner_id=owner_id,
            platform=str(getattr(item, "platform")),
            source_url=str(getattr(item, "url") or ""),
            content_type="post",
            title=str(getattr(item, "title") or ""),
            content=str(getattr(item, "content") or ""),
            author=getattr(item, "author"),
            publish_time=getattr(item, "publish_time"),
            metrics={
                "likes": int(getattr(item, "like_count") or 0),
                "comments": int(getattr(item, "comment_count") or 0),
                "favorites": int(getattr(item, "collect_count") or 0),
                "shares": int(getattr(item, "share_count") or 0),
            },
            source_type="inbox",
            manual_note=remark,
        )
        db.add(asset)
        db.flush()
        return int(getattr(asset, "id"))

    @staticmethod
    def _build_insight_item(db: Session, owner_id: int, item: MaterialInbox,
                             topic_name: Optional[str], manual_note: Optional[str]) -> int:
        insight = InsightService.ingest_item(
            db=db,
            owner_id=owner_id,
            platform=str(getattr(item, "platform")),
            title=str(getattr(item, "title") or ""),
            body_text=str(getattr(item, "content") or ""),
            source_url=str(getattr(item, "url") or "") or None,
            author_name=getattr(item, "author"),
            publish_time=getattr(item, "publish_time"),
            like_count=int(getattr(item, "like_count") or 0),
            comment_count=int(getattr(item, "comment_count") or 0),
            share_count=int(getattr(item, "share_count") or 0),
            collect_count=int(getattr(item, "collect_count") or 0),
            topic_name=topic_name,
            manual_note=manual_note,
            source_type="inbox",
            raw_payload=getattr(item, "raw_data") or {},
        )
        return int(getattr(insight, "id"))

    @staticmethod
    def approve_item(
        db: Session,
        owner_id: int,
        inbox_id: int,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        """审核通过：入素材库（ContentAsset）+ 洞察库（InsightContentItem）。"""
        item = AcquisitionIntakeService._get_pending_item(db, owner_id, inbox_id)
        content_asset_id = AcquisitionIntakeService._build_content_asset(db, owner_id, item, remark)
        insight_item_id = AcquisitionIntakeService._build_insight_item(db, owner_id, item, None, remark)
        setattr(item, "status", "approved")
        if remark:
            setattr(item, "remark", remark)
        db.commit()
        return {"inbox_id": inbox_id, "status": "approved",
                "content_asset_id": content_asset_id, "insight_item_id": insight_item_id}

    @staticmethod
    def to_topic_item(
        db: Session,
        owner_id: int,
        inbox_id: int,
        topic_id: int,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        """挂主题：入素材库 + 洞察库并绑定指定主题。"""
        item = AcquisitionIntakeService._get_pending_item(db, owner_id, inbox_id)
        topic = db.query(InsightTopic).filter(InsightTopic.id == topic_id).first()
        if topic is None:
            raise ValueError(f"主题 {topic_id} 不存在")
        topic_name = str(getattr(topic, "name"))
        content_asset_id = AcquisitionIntakeService._build_content_asset(db, owner_id, item, remark)
        insight_item_id = AcquisitionIntakeService._build_insight_item(db, owner_id, item, topic_name, remark)
        setattr(item, "status", "approved")
        if remark:
            setattr(item, "remark", remark)
        db.commit()
        return {"inbox_id": inbox_id, "status": "approved", "topic_id": topic_id,
                "content_asset_id": content_asset_id, "insight_item_id": insight_item_id}

    @staticmethod
    def to_negative_case_item(
        db: Session,
        owner_id: int,
        inbox_id: int,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        """标记为反案例：入洞察库，manual_note 前缀 [反案例]，不创建 ContentAsset。"""
        item = AcquisitionIntakeService._get_pending_item(db, owner_id, inbox_id)
        neg_note = f"[反案例] {remark}" if remark else "[反案例]"
        insight_item_id = AcquisitionIntakeService._build_insight_item(
            db, owner_id, item, None, neg_note
        )
        setattr(item, "status", "negative_case")
        if remark:
            setattr(item, "remark", remark)
        db.commit()
        return {"inbox_id": inbox_id, "status": "negative_case", "insight_item_id": insight_item_id}

    @staticmethod
    def discard_item(
        db: Session,
        owner_id: int,
        inbox_id: int,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        """丢弃：仅修改状态，不创建任何下游记录。"""
        item = AcquisitionIntakeService._get_pending_item(db, owner_id, inbox_id)
        setattr(item, "status", "discarded")
        if remark:
            setattr(item, "remark", remark)
        db.commit()
        return {"inbox_id": inbox_id, "status": "discarded"}

    @staticmethod
    def submit_manual(
        db: Session,
        owner_id: int,
        platform: str,
        title: str,
        content: str,
        tags: Optional[list] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """手动录入内容直接写入收件箱，等待人工审核。"""
        inbox = MaterialInbox(
            owner_id=owner_id,
            source_channel="manual_input",
            platform=platform,
            title=title,
            content=content,
            raw_data={"tags": tags or []},
            status="pending",
            remark=note,
        )
        db.add(inbox)
        db.commit()
        db.refresh(inbox)
        return {"inbox_id": int(getattr(inbox, "id")), "status": "pending"}
