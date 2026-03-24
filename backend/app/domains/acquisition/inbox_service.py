from collections import defaultdict
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.domains.acquisition.collect_service import CollectService
from app.models import ContentAsset, InboxItem, User
from app.services.insight_service import InsightService


class InboxService:
    @staticmethod
    def _normalize_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            parsed = urlparse(url.strip())
            normalized = parsed._replace(query="", fragment="")
            return urlunparse(normalized)
        except Exception:
            return url.strip()

    @staticmethod
    def create_item(db: Session, user_id: int, payload: Dict[str, Any]) -> InboxItem:
        payload_data = dict(payload)
        category = payload_data.pop("category", None) or CollectService.auto_category(
            payload_data["title"], payload_data["content"]
        )
        item = InboxItem(
            owner_id=user_id,
            category=category,
            **payload_data,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def list_items_by_ids(db: Session, user_id: int, inbox_ids: list[int]) -> list[InboxItem]:
        if not inbox_ids:
            return []
        return (
            db.query(InboxItem)
            .filter(InboxItem.owner_id == user_id, InboxItem.id.in_(inbox_ids))
            .all()
        )

    @staticmethod
    def get_item(db: Session, user_id: int, inbox_id: int) -> InboxItem:
        item = (
            db.query(InboxItem)
            .filter(InboxItem.id == inbox_id, InboxItem.owner_id == user_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="收件箱条目不存在")
        return item

    @staticmethod
    def list_items(
        db: Session,
        user_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[InboxItem]:
        query = db.query(InboxItem).filter(InboxItem.owner_id == user_id)
        if status and status != "all":
            query = query.filter(InboxItem.status == status)
        if platform and platform != "all":
            query = query.filter(InboxItem.platform == platform)
        if search:
            query = query.filter(
                or_(
                    InboxItem.title.ilike(f"%{search}%"),
                    InboxItem.content.ilike(f"%{search}%"),
                )
            )
        return query.order_by(InboxItem.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_stats(db: Session, user_id: int) -> Dict[str, Any]:
        total = db.query(InboxItem).filter(InboxItem.owner_id == user_id).count()
        by_status = (
            db.query(InboxItem.status, func.count(InboxItem.id))
            .filter(InboxItem.owner_id == user_id)
            .group_by(InboxItem.status)
            .all()
        )
        by_platform = (
            db.query(InboxItem.platform, func.count(InboxItem.id))
            .filter(InboxItem.owner_id == user_id)
            .group_by(InboxItem.platform)
            .all()
        )
        status_map = {key: count for key, count in by_status if key}
        return {
            "total": total,
            "pending": status_map.get("pending", 0),
            "analyzed": status_map.get("analyzed", 0),
            "imported": status_map.get("imported", 0),
            "discarded": status_map.get("discarded", 0),
            "by_platform": {key: count for key, count in by_platform if key},
        }

    @staticmethod
    async def analyze_item(
        db: Session,
        item: InboxItem,
        ai_service,
        force_cloud: bool = False,
        user_id: Optional[int] = None,
    ) -> InboxItem:
        temp_asset = ContentAsset(
            owner_id=item.owner_id,
            platform=item.platform,
            source_url=item.source_url,
            content_type=item.content_type,
            title=item.title,
            content=item.content,
            author=item.author,
            publish_time=item.publish_time,
            tags=item.tags or [],
            metrics=item.metrics or {},
            source_type=item.source_type,
            category=item.category,
            manual_note=item.manual_note,
        )
        result = await CollectService.analyze_with_ai(temp_asset, ai_service, force_cloud, user_id)
        item.tags = result.get("tags") or item.tags
        item.category = result.get("category") or item.category
        item.heat_score = float(result.get("heat_score") or 0.0)
        item.is_viral = bool(result.get("is_viral") or False)
        item.status = "analyzed"
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_item(db: Session, item: InboxItem, payload: Dict[str, Any]) -> InboxItem:
        assignee_user_id = payload.pop("assignee_user_id", None)
        if assignee_user_id is not None:
            assignee = db.query(User).filter(User.id == assignee_user_id).first()
            if not assignee:
                raise HTTPException(status_code=404, detail="分拣责任人不存在")
            item.assigned_to = assignee.id
            item.assigned_at = func.now()

        for field, value in payload.items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def promote_item(db: Session, item: InboxItem) -> Dict[str, int | str]:
        if item.status == "discarded":
            raise HTTPException(status_code=400, detail="已丢弃条目不能入库")
        if item.promoted_content_id and item.promoted_insight_item_id:
            item.status = "imported"
            db.commit()
            return {
                "inbox_id": item.id,
                "status": item.status,
                "content_asset_id": item.promoted_content_id,
                "insight_item_id": item.promoted_insight_item_id,
            }

        content_asset = ContentAsset(
            owner_id=item.owner_id,
            platform=item.platform,
            source_url=item.source_url,
            content_type=item.content_type,
            title=item.title,
            content=item.content,
            author=item.author,
            publish_time=item.publish_time,
            tags=item.tags or [],
            metrics=item.metrics or {},
            heat_score=item.heat_score or 0.0,
            is_viral=item.is_viral or False,
            source_type=item.source_type,
            category=item.category,
            manual_note=item.manual_note,
        )
        db.add(content_asset)
        db.commit()
        db.refresh(content_asset)

        insight_item = InsightService.ingest_item(
            db,
            owner_id=item.owner_id,
            platform=item.platform,
            title=item.title,
            body_text=item.content,
            source_url=item.source_url,
            content_type=item.content_type,
            author_name=item.author,
            publish_time=item.publish_time,
            manual_note=item.manual_note,
            source_type=item.source_type or "manual",
            raw_payload={"from": "inbox", "inbox_id": item.id},
        )

        item.promoted_content_id = content_asset.id
        item.promoted_insight_item_id = insight_item.id
        item.status = "imported"
        db.commit()
        db.refresh(item)
        return {
            "inbox_id": item.id,
            "status": item.status,
            "content_asset_id": content_asset.id,
            "insight_item_id": insight_item.id,
        }

    @staticmethod
    def discard_item(db: Session, item: InboxItem, review_note: Optional[str] = None) -> InboxItem:
        item.status = "discarded"
        if review_note:
            item.review_note = review_note
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def batch_assign(
        db: Session,
        user_id: int,
        inbox_ids: list[int],
        assignee_user_id: int,
        note_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        assignee = db.query(User).filter(User.id == assignee_user_id).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="分拣责任人不存在")

        items = InboxService.list_items_by_ids(db, user_id, inbox_ids)
        item_map = {item.id: item for item in items}
        details: list[dict[str, Any]] = []
        success = 0

        for inbox_id in inbox_ids:
            item = item_map.get(inbox_id)
            if not item:
                details.append({"inbox_id": inbox_id, "ok": False, "error": "not_found"})
                continue
            if item.status in ("imported", "discarded"):
                details.append({
                    "inbox_id": inbox_id,
                    "ok": False,
                    "error": f"status_{item.status}_locked",
                })
                continue

            item.assigned_to = assignee.id
            item.assigned_at = func.now()

            base_note = f"[ASSIGN] @{assignee.username}"
            if note_template:
                base_note = f"{base_note} {note_template}"
            item.review_note = base_note
            success += 1
            details.append(
                {
                    "inbox_id": inbox_id,
                    "ok": True,
                    "status": item.status,
                    "assigned_to": assignee.id,
                }
            )

        db.commit()
        return {
            "total": len(inbox_ids),
            "success": success,
            "failed": len(inbox_ids) - success,
            "details": details,
        }

    @staticmethod
    def batch_discard(
        db: Session,
        user_id: int,
        inbox_ids: list[int],
        review_note: str,
    ) -> Dict[str, Any]:
        items = InboxService.list_items_by_ids(db, user_id, inbox_ids)
        item_map = {item.id: item for item in items}
        details: list[dict[str, Any]] = []
        success = 0

        for inbox_id in inbox_ids:
            item = item_map.get(inbox_id)
            if not item:
                details.append({"inbox_id": inbox_id, "ok": False, "error": "not_found"})
                continue
            if item.status == "imported":
                details.append({"inbox_id": inbox_id, "ok": False, "error": "already_imported"})
                continue
            item.status = "discarded"
            item.review_note = review_note
            success += 1
            details.append({"inbox_id": inbox_id, "ok": True, "status": item.status})

        db.commit()
        return {
            "total": len(inbox_ids),
            "success": success,
            "failed": len(inbox_ids) - success,
            "details": details,
        }

    @staticmethod
    def batch_promote(db: Session, user_id: int, inbox_ids: list[int]) -> Dict[str, Any]:
        items = InboxService.list_items_by_ids(db, user_id, inbox_ids)
        item_map = {item.id: item for item in items}
        details: list[dict[str, Any]] = []
        success = 0

        for inbox_id in inbox_ids:
            item = item_map.get(inbox_id)
            if not item:
                details.append({"inbox_id": inbox_id, "ok": False, "error": "not_found"})
                continue
            try:
                result = InboxService.promote_item(db, item)
                success += 1
                details.append({"inbox_id": inbox_id, "ok": True, "result": result})
            except HTTPException as exc:
                details.append({
                    "inbox_id": inbox_id,
                    "ok": False,
                    "error": exc.detail,
                    "status_code": exc.status_code,
                })

        return {
            "total": len(inbox_ids),
            "success": success,
            "failed": len(inbox_ids) - success,
            "details": details,
        }

    @staticmethod
    def dedupe_preview(db: Session, user_id: int) -> Dict[str, Any]:
        rows = (
            db.query(InboxItem)
            .filter(InboxItem.owner_id == user_id, InboxItem.status.in_(["pending", "analyzed"]))
            .order_by(InboxItem.created_at.desc())
            .all()
        )

        groups: dict[str, list[InboxItem]] = defaultdict(list)
        for row in rows:
            key = InboxService._normalize_url(row.source_url)
            if not key:
                key = f"title::{(row.title or '').strip().lower()[:80]}"
            groups[key].append(row)

        duplicate_groups: list[dict[str, Any]] = []
        total_duplicates = 0
        for key, items in groups.items():
            if len(items) <= 1:
                continue
            total_duplicates += len(items)
            duplicate_groups.append(
                {
                    "key": key,
                    "count": len(items),
                    "inbox_ids": [item.id for item in items],
                    "titles": [item.title for item in items[:5]],
                }
            )

        duplicate_groups.sort(key=lambda x: x["count"], reverse=True)
        return {
            "duplicate_groups": duplicate_groups,
            "total_duplicates": total_duplicates,
        }

    @staticmethod
    def auto_merge_duplicates(
        db: Session,
        user_id: int,
        keep_strategy: str = "latest",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        preview = InboxService.dedupe_preview(db, user_id)
        details: list[dict[str, Any]] = []
        merged = 0

        for group in preview["duplicate_groups"]:
            inbox_ids = group["inbox_ids"]
            rows = (
                db.query(InboxItem)
                .filter(InboxItem.owner_id == user_id, InboxItem.id.in_(inbox_ids))
                .order_by(InboxItem.created_at.desc())
                .all()
            )
            if len(rows) <= 1:
                continue

            keeper = rows[0] if keep_strategy == "latest" else rows[-1]
            to_discard = [row for row in rows if row.id != keeper.id]

            if not dry_run:
                for row in to_discard:
                    row.status = "discarded"
                    row.review_note = f"[AUTO_MERGED] merged_into={keeper.id}"
                db.flush()

            merged += len(to_discard)
            details.append(
                {
                    "key": group["key"],
                    "kept_inbox_id": keeper.id,
                    "merged_inbox_ids": [row.id for row in to_discard],
                    "dry_run": dry_run,
                }
            )

        if not dry_run:
            db.commit()

        return {
            "total": len(preview["duplicate_groups"]),
            "success": len(details),
            "failed": 0,
            "details": details,
            "merged_count": merged,
            "dry_run": dry_run,
        }