from __future__ import annotations

from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import re
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import (
    CollectTask,
    EmployeeLinkSubmission,
    GenerationTask,
    KnowledgeChunk,
    KnowledgeDocument,
    MaterialItem,
    NormalizedContent,
    PromptTemplate,
    Rule,
    SourceContent,
)
from app.services.collector.browser_collector_client import BrowserCollectorClient


class AcquisitionIntakeService:
    """First-principles acquisition pipeline: source -> normalized -> material -> knowledge -> generation."""

    _TARGET_TERMS = ["贷款", "资金", "征信", "负债", "网贷", "融资", "周转"]
    _INTENT_TERMS = ["怎么办", "求助", "急需", "有没有", "推荐", "私信", "加微", "联系"]
    _STATUS_TRANSITIONS: dict[str, set[str]] = {
        "pending": {"review", "discard"},
        "review": {"pending", "discard"},
        "discard": {"pending", "review"},
    }
    _ACCOUNT_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("顾问号", ("方案", "怎么做", "怎么办", "顾问", "办理", "测额")),
        ("法务号", ("法务", "协商", "律师", "诉讼", "法条")),
        ("引流号", ("私信", "加微信", "主页", "评论区", "咨询我")),
        ("科普号", ("科普", "知识", "解析", "注意", "避坑")),
    ]
    _AUDIENCE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("负债逾期", ("逾期", "负债", "催收", "协商", "延期")),
        ("征信问题", ("征信", "查询多", "花户", "黑户", "征信花")),
        ("创业周转", ("创业", "周转", "流水", "企业贷", "营业执照")),
        ("宝妈", ("宝妈", "带娃", "全职妈妈", "母婴")),
    ]
    _CONTENT_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("案例", ("案例", "真实经历", "成功", "上岸")),
        ("评论洞察", ("评论区", "网友", "留言", "评论")),
        ("规则说明", ("规则", "要求", "条件", "门槛")),
    ]

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _split_keywords(keyword: str) -> list[str]:
        text = keyword.strip()
        if not text:
            return []
        return [seg.strip() for seg in re.split(r"[\s,，;；|/]+", text) if seg.strip()]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        cleaned = AcquisitionIntakeService._normalize_text(text).lower()
        if not cleaned:
            return []

        tokens: list[str] = []
        for token in re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", cleaned):
            tokens.append(token)
            if re.fullmatch(r"[\u4e00-\u9fff]{2,}", token):
                for size in (2, 3):
                    for idx in range(0, max(len(token) - size + 1, 0)):
                        tokens.append(token[idx: idx + size])
        return tokens

    @staticmethod
    def _extract_keywords(text: str, limit: int = 12) -> list[str]:
        counter = Counter(AcquisitionIntakeService._tokenize(text))
        return [token for token, _ in counter.most_common(limit)]

    @staticmethod
    def _build_content_hash(title: str, content: str, source_url: Optional[str]) -> str:
        payload = "\n".join([
            AcquisitionIntakeService._normalize_text(title),
            AcquisitionIntakeService._normalize_text(content),
            AcquisitionIntakeService._normalize_text(source_url),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_collected_item(platform: str, keyword: str, item: dict[str, Any]) -> dict[str, Any]:
        source_id = item.get("source_id") or item.get("sourceId") or item.get("external_id") or item.get("id")
        url = item.get("url") or item.get("source_url")
        title = item.get("title") or item.get("raw_title")
        content_text = item.get("content_text") or item.get("content") or item.get("snippet") or item.get("desc")
        normalized_platform = AcquisitionIntakeService._normalize_text(item.get("platform") or platform or "other") or "other"

        return {
            "platform": normalized_platform,
            "keyword": AcquisitionIntakeService._normalize_text(keyword) or None,
            "source_id": AcquisitionIntakeService._normalize_text(source_id) or None,
            "source_url": AcquisitionIntakeService._normalize_text(url) or None,
            "title": AcquisitionIntakeService._normalize_text(title) or None,
            "author_name": AcquisitionIntakeService._normalize_text(item.get("author_name") or item.get("author") or item.get("nickname")) or None,
            "content_text": AcquisitionIntakeService._normalize_text(content_text) or None,
            "cover_url": AcquisitionIntakeService._normalize_text(item.get("cover_url")) or None,
            "publish_time": AcquisitionIntakeService._to_datetime(item.get("publish_time") or item.get("upload_time")),
            "like_count": AcquisitionIntakeService._to_int(item.get("like_count") or item.get("liked_count")),
            "comment_count": AcquisitionIntakeService._to_int(item.get("comment_count")),
            "favorite_count": AcquisitionIntakeService._to_int(item.get("collect_count") or item.get("favorite_count") or item.get("collected_count")),
            "share_count": AcquisitionIntakeService._to_int(item.get("share_count")),
            "parse_status": AcquisitionIntakeService._normalize_text(item.get("parse_status") or "success").lower() or "success",
            "risk_status": AcquisitionIntakeService._normalize_text(item.get("risk_status") or "safe").lower() or "safe",
            "raw_payload": item,
        }

    @staticmethod
    def _validate_required_fields(normalized: dict[str, Any], source_channel: str) -> Optional[str]:
        if not normalized.get("platform"):
            return "missing_platform"
        if not normalized.get("title") and not normalized.get("content_text"):
            return "missing_title_and_content"
        if source_channel in {"collect_task", "employee_submission", "wechat_robot"}:
            if not normalized.get("source_url"):
                return "missing_url"
        return None

    @staticmethod
    def _calculate_quality(normalized: dict[str, Any]) -> int:
        score = 0
        if normalized.get("title"):
            score += 20
        if normalized.get("content_text"):
            score += 30
            content_length = len(str(normalized["content_text"]))
            if content_length >= 80:
                score += 15
            if content_length >= 200:
                score += 15
        if normalized.get("author_name"):
            score += 10
        if normalized.get("publish_time"):
            score += 5
        if normalized.get("cover_url"):
            score += 5
        return min(score, 100)

    @staticmethod
    def _calculate_relevance(normalized: dict[str, Any], keyword: str) -> int:
        text = f"{normalized.get('title') or ''} {normalized.get('content_text') or ''}"
        score = 0
        for token in AcquisitionIntakeService._split_keywords(keyword):
            if token and token in text:
                score += 30
        for term in AcquisitionIntakeService._TARGET_TERMS:
            if term in text:
                score += 12
        return min(score, 100)

    @staticmethod
    def _calculate_lead_score(normalized: dict[str, Any]) -> tuple[int, str, str]:
        text = f"{normalized.get('title') or ''} {normalized.get('content_text') or ''}"
        score = 0
        matched_terms: list[str] = []
        for word in AcquisitionIntakeService._INTENT_TERMS:
            if word in text:
                matched_terms.append(word)
                score += 20
        if any(term in text for term in ("电话", "微信", "私信", "联系")):
            matched_terms.append("联系方式线索")
            score += 20

        score = min(score, 100)
        if score >= 70:
            level = "high"
        elif score >= 35:
            level = "medium"
        else:
            level = "low"
        reason = "、".join(matched_terms[:3]) if matched_terms else "未识别显著转化信号"
        return score, level, reason

    @staticmethod
    def _calculate_hot_level(normalized: dict[str, Any]) -> str:
        score = (
            AcquisitionIntakeService._to_int(normalized.get("favorite_count")) * 3
            + AcquisitionIntakeService._to_int(normalized.get("comment_count")) * 2
            + AcquisitionIntakeService._to_int(normalized.get("share_count")) * 2
            + AcquisitionIntakeService._to_int(normalized.get("like_count"))
        )
        if score >= 200:
            return "high"
        if score >= 60:
            return "medium"
        return "low"

    @staticmethod
    def _classify_account_type(text: str) -> str:
        for label, words in AcquisitionIntakeService._ACCOUNT_TYPE_RULES:
            if any(word in text for word in words):
                return label
        return "科普号"

    @staticmethod
    def _classify_target_audience(text: str) -> str:
        for label, words in AcquisitionIntakeService._AUDIENCE_RULES:
            if any(word in text for word in words):
                return label
        return "泛人群"

    @staticmethod
    def _classify_content_type(title: str, content: str) -> str:
        text = f"{title} {content}"
        for label, words in AcquisitionIntakeService._CONTENT_TYPE_RULES:
            if any(word in text for word in words):
                return label
        if not content:
            return "标题"
        return "正文"

    @staticmethod
    def _extract_topic(title: str, content: str) -> str:
        keywords = AcquisitionIntakeService._extract_keywords(f"{title} {content}", limit=5)
        return " / ".join(keywords[:3]) if keywords else "未分类主题"

    @staticmethod
    def _split_chunks(text: str, chunk_size: int = 300) -> list[str]:
        body = AcquisitionIntakeService._normalize_text(text)
        if not body:
            return []
        paragraphs = [seg.strip() for seg in re.split(r"\n+", body) if seg.strip()]
        if not paragraphs:
            paragraphs = [body]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if not current:
                current = paragraph
                continue
            if len(current) + len(paragraph) + 1 <= chunk_size:
                current = f"{current}\n{paragraph}"
            else:
                chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks[:20]

    @staticmethod
    def _decide_status(
        source_channel: str,
        normalized: dict[str, Any],
        quality_score: int,
        relevance_score: int,
        lead_score: int,
        validation_reason: Optional[str],
    ) -> tuple[str, str]:
        if validation_reason:
            return "discard", validation_reason

        risk_status = normalized.get("risk_status") or "safe"
        parse_status = normalized.get("parse_status") or "success"

        if risk_status in {"blocked", "high", "reject"}:
            return "discard", "risk_blocked"
        if quality_score < 30:
            return "discard", "low_quality"
        if source_channel == "manual_input":
            return "review", "manual_input"
        if parse_status in {"list_only", "detail_failed", "partial"}:
            return "review", "detail_not_complete"
        if risk_status in {"review", "medium"}:
            return "review", "risk_need_review"
        if relevance_score == 0 and source_channel == "collect_task":
            return "discard", "irrelevant"
        if lead_score < 20:
            return "review", "lead_need_review"
        return "pending", "passed"

    @staticmethod
    def _find_duplicate_material(
        db: Session,
        owner_id: int,
        platform: str,
        source_id: Optional[str],
        content_hash: str,
    ) -> Optional[MaterialItem]:
        if source_id:
            existing_by_source = (
                db.query(MaterialItem)
                .filter(
                    MaterialItem.owner_id == owner_id,
                    MaterialItem.platform == platform,
                    MaterialItem.source_id == source_id,
                )
                .order_by(MaterialItem.id.desc())
                .first()
            )
            if existing_by_source is not None:
                return existing_by_source

        existing_by_hash = (
            db.query(MaterialItem)
            .join(NormalizedContent, MaterialItem.normalized_content_id == NormalizedContent.id)
            .filter(
                MaterialItem.owner_id == owner_id,
                MaterialItem.platform == platform,
                NormalizedContent.content_hash == content_hash,
            )
            .order_by(MaterialItem.id.desc())
            .first()
        )
        return existing_by_hash

    @staticmethod
    def _create_source_content(
        db: Session,
        owner_id: int,
        source_channel: str,
        normalized: dict[str, Any],
        source_task_id: Optional[int],
        source_submission_id: Optional[int],
        submitted_by_employee_id: Optional[int],
        remark: Optional[str],
    ) -> SourceContent:
        source = SourceContent(
            owner_id=owner_id,
            source_channel=source_channel,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            source_type="crawler" if source_channel in {"collect_task", "employee_submission", "wechat_robot"} else "manual",
            source_platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            keyword=normalized.get("keyword"),
            raw_title=normalized.get("title"),
            raw_content=normalized.get("content_text"),
            raw_payload=normalized.get("raw_payload") or {},
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            remark=remark,
        )
        db.add(source)
        db.flush()
        return source

    @staticmethod
    def _create_normalized_content(
        db: Session,
        owner_id: int,
        source: SourceContent,
        normalized: dict[str, Any],
        content_hash: str,
    ) -> NormalizedContent:
        title = normalized.get("title") or (normalized.get("content_text") or "")[:20] or "无标题"
        content_text = normalized.get("content_text") or normalized.get("title") or ""
        normalized_content = NormalizedContent(
            owner_id=owner_id,
            source_content_id=source.id,
            title=title,
            content_text=content_text,
            content_preview=content_text[:100],
            content_hash=content_hash,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            keyword=normalized.get("keyword"),
        )
        db.add(normalized_content)
        db.flush()
        return normalized_content

    @staticmethod
    def _replace_knowledge(
        db: Session,
        owner_id: int,
        material: MaterialItem,
    ) -> KnowledgeDocument:
        for existing in list(material.knowledge_documents or []):
            db.delete(existing)
        db.flush()

        text = f"{material.title or ''}\n{material.content_text or ''}"
        document = KnowledgeDocument(
            owner_id=owner_id,
            material_item_id=material.id,
            platform=material.platform,
            account_type=AcquisitionIntakeService._classify_account_type(text),
            target_audience=AcquisitionIntakeService._classify_target_audience(text),
            content_type=AcquisitionIntakeService._classify_content_type(material.title or "", material.content_text or ""),
            topic=AcquisitionIntakeService._extract_topic(material.title or "", material.content_text or ""),
            title=material.title,
            summary=(material.content_text or material.content_preview or "")[:120],
            content_text=material.content_text,
        )
        db.add(document)
        db.flush()

        for idx, chunk_text in enumerate(AcquisitionIntakeService._split_chunks(material.content_text or ""), start=1):
            db.add(
                KnowledgeChunk(
                    owner_id=owner_id,
                    knowledge_document_id=document.id,
                    chunk_type="body",
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    keywords=AcquisitionIntakeService._extract_keywords(chunk_text, limit=8),
                )
            )

        return document

    @staticmethod
    def _process_item(
        db: Session,
        owner_id: int,
        source_channel: str,
        raw_item: dict[str, Any],
        platform: str,
        keyword: str,
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        normalized = AcquisitionIntakeService._normalize_collected_item(platform, keyword, raw_item)
        validation_reason = AcquisitionIntakeService._validate_required_fields(normalized, source_channel)
        content_hash = AcquisitionIntakeService._build_content_hash(
            normalized.get("title") or "",
            normalized.get("content_text") or "",
            normalized.get("source_url"),
        )

        source = AcquisitionIntakeService._create_source_content(
            db=db,
            owner_id=owner_id,
            source_channel=source_channel,
            normalized=normalized,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            remark=remark,
        )
        normalized_content = AcquisitionIntakeService._create_normalized_content(db, owner_id, source, normalized, content_hash)

        duplicate = AcquisitionIntakeService._find_duplicate_material(
            db=db,
            owner_id=owner_id,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            content_hash=content_hash,
        )
        if duplicate is not None:
            return {
                "created": False,
                "duplicate": True,
                "material": duplicate,
                "status": "discard",
                "reason": "duplicate",
            }

        quality_score = AcquisitionIntakeService._calculate_quality(normalized)
        relevance_score = AcquisitionIntakeService._calculate_relevance(normalized, keyword)
        lead_score, lead_level, lead_reason = AcquisitionIntakeService._calculate_lead_score(normalized)
        status, reason = AcquisitionIntakeService._decide_status(
            source_channel=source_channel,
            normalized=normalized,
            quality_score=quality_score,
            relevance_score=relevance_score,
            lead_score=lead_score,
            validation_reason=validation_reason,
        )
        title = normalized.get("title") or (normalized.get("content_text") or "")[:20] or "无标题"
        content_text = normalized.get("content_text") or title

        material = MaterialItem(
            owner_id=owner_id,
            source_channel=source_channel,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            source_content_id=source.id,
            normalized_content_id=normalized_content.id,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            keyword=normalized.get("keyword"),
            title=title,
            content_text=content_text,
            content_preview=content_text[:100],
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            hot_level=AcquisitionIntakeService._calculate_hot_level(normalized),
            lead_level=lead_level,
            lead_reason=lead_reason,
            quality_score=quality_score,
            relevance_score=relevance_score,
            lead_score=lead_score,
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            is_duplicate=False,
            filter_reason=reason,
            status=status,
            remark=remark,
        )
        db.add(material)
        db.flush()
        AcquisitionIntakeService._replace_knowledge(db, owner_id, material)

        return {
            "created": True,
            "duplicate": False,
            "material": material,
            "status": status,
            "reason": reason,
        }

    @staticmethod
    def serialize_material_item(item: MaterialItem, include_raw_data: bool = True) -> dict[str, Any]:
        created_at = getattr(item, "created_at", None)
        updated_at = getattr(item, "updated_at", None)
        publish_time = getattr(item, "publish_time", None)
        raw_data: dict[str, Any] = {}
        if include_raw_data:
            source = getattr(item, "source_content", None)
            raw_data = getattr(source, "raw_payload", None) or {}

        return {
            "id": item.id,
            "source_channel": item.source_channel,
            "source_task_id": item.source_task_id,
            "source_submission_id": item.source_submission_id,
            "platform": item.platform,
            "source_id": item.source_id,
            "keyword": item.keyword,
            "title": item.title,
            "author": item.author_name,
            "content": item.content_text,
            "url": item.source_url,
            "cover_url": item.cover_url,
            "like_count": item.like_count,
            "comment_count": item.comment_count,
            "collect_count": item.favorite_count,
            "share_count": item.share_count,
            "publish_time": publish_time.isoformat() if publish_time else None,
            "parse_status": item.parse_status,
            "risk_status": item.risk_status,
            "quality_score": item.quality_score,
            "relevance_score": item.relevance_score,
            "lead_score": item.lead_score,
            "lead_level": item.lead_level,
            "lead_reason": item.lead_reason,
            "hot_level": item.hot_level,
            "is_duplicate": bool(item.is_duplicate),
            "filter_reason": item.filter_reason,
            "raw_data": raw_data,
            "status": item.status,
            "submitted_by_employee_id": item.submitted_by_employee_id,
            "remark": item.remark,
            "review_note": item.review_note,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    @staticmethod
    def _ingest_items(
        db: Session,
        owner_id: int,
        source_channel: str,
        items: list[dict[str, Any]],
        platform: str,
        keyword: str,
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> dict[str, int]:
        stats = {
            "inserted_count": 0,
            "review_count": 0,
            "discard_count": 0,
            "duplicate_count": 0,
            "failed_count": 0,
        }

        for raw in items:
            try:
                result = AcquisitionIntakeService._process_item(
                    db=db,
                    owner_id=owner_id,
                    source_channel=source_channel,
                    raw_item=raw,
                    platform=platform,
                    keyword=keyword,
                    source_task_id=source_task_id,
                    source_submission_id=source_submission_id,
                    submitted_by_employee_id=submitted_by_employee_id,
                    remark=remark,
                )
                if result["duplicate"]:
                    stats["duplicate_count"] += 1
                    continue
                if result["status"] == "pending":
                    stats["inserted_count"] += 1
                elif result["status"] == "review":
                    stats["review_count"] += 1
                else:
                    stats["discard_count"] += 1
            except Exception:
                stats["failed_count"] += 1

        db.commit()
        return stats

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
        task_id = int(task.id)

        try:
            result = collector_client.collect_keyword(platform=platform, keyword=keyword, max_items=max_items)
            rows = result.get("items") or []
            stats = AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel="collect_task",
                items=rows,
                platform=platform,
                keyword=keyword,
                source_task_id=task_id,
            )
            task.result_count = int(result.get("count") or result.get("total") or len(rows))
            task.inserted_count = stats["inserted_count"]
            task.review_count = stats["review_count"]
            task.discard_count = stats["discard_count"]
            task.duplicate_count = stats["duplicate_count"]
            task.failed_count = stats["failed_count"]
            task.status = "success"
            db.commit()
            db.refresh(task)
            return {
                "task_id": task_id,
                "status": task.status,
                "result_count": task.result_count,
                "inserted": task.inserted_count,
                "review": task.review_count,
                "discard": task.discard_count,
                "duplicate": task.duplicate_count,
                "failed": task.failed_count,
            }
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
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
        submission_id = int(submission.id)

        try:
            result = collector_client.collect_single_link(url=url)
            rows = result.get("items") or []
            if not rows:
                raise ValueError("采集服务未返回可入库内容")

            row = rows[0]
            platform = AcquisitionIntakeService._normalize_text(row.get("platform") or "other") or "other"
            submission.platform = platform
            channel = "wechat_robot" if source_type == "wechat_robot" else "employee_submission"
            stats = AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel=channel,
                items=[row],
                platform=platform,
                keyword=url,
                source_submission_id=submission_id,
                submitted_by_employee_id=employee_id,
                remark=note,
            )
            submission.status = "success"
            db.commit()
            return {
                "submission_id": submission_id,
                "status": submission.status,
                "platform": submission.platform,
                "inserted": stats["inserted_count"],
                "review": stats["review_count"],
                "discard": stats["discard_count"],
                "duplicate": stats["duplicate_count"],
            }
        except Exception as exc:
            submission.status = "failed"
            submission.error_message = str(exc)
            db.commit()
            raise

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
        raw_item = {
            "platform": platform,
            "title": title,
            "content_text": content,
            "parse_status": "success",
            "risk_status": "review",
            "raw_payload": {"tags": tags or []},
        }
        result = AcquisitionIntakeService._process_item(
            db=db,
            owner_id=owner_id,
            source_channel="manual_input",
            raw_item=raw_item,
            platform=platform,
            keyword="",
            remark=note,
        )
        db.commit()
        material = result["material"]
        return {"inbox_id": int(material.id), "material_id": int(material.id), "status": str(material.status)}

    @staticmethod
    def list_inbox(
        db: Session,
        owner_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        source_channel: Optional[str] = None,
        keyword: Optional[str] = None,
        risk_status: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MaterialItem]:
        query = db.query(MaterialItem).filter(MaterialItem.owner_id == owner_id)
        if status:
            query = query.filter(MaterialItem.status == status)
        if platform:
            query = query.filter(MaterialItem.platform == platform)
        if source_channel:
            query = query.filter(MaterialItem.source_channel == source_channel)
        if keyword:
            query = query.filter(MaterialItem.keyword.contains(keyword))
        if risk_status:
            query = query.filter(MaterialItem.risk_status == risk_status)
        if is_duplicate is not None:
            query = query.filter(MaterialItem.is_duplicate == is_duplicate)
        return query.order_by(desc(MaterialItem.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_inbox_item(db: Session, owner_id: int, inbox_id: int) -> Optional[MaterialItem]:
        return (
            db.query(MaterialItem)
            .filter(MaterialItem.owner_id == owner_id, MaterialItem.id == inbox_id)
            .first()
        )

    @staticmethod
    def get_material_item(db: Session, owner_id: int, material_id: int) -> Optional[MaterialItem]:
        return AcquisitionIntakeService.get_inbox_item(db, owner_id, material_id)

    @staticmethod
    def reindex_material(db: Session, owner_id: int, material_id: int) -> dict[str, Any]:
        material = AcquisitionIntakeService.get_material_item(db, owner_id, material_id)
        if material is None:
            raise ValueError("素材不存在")

        document = AcquisitionIntakeService._replace_knowledge(db, owner_id, material)
        db.commit()
        db.refresh(material)
        return {
            "material_id": material.id,
            "knowledge_document_id": document.id,
            "account_type": document.account_type,
            "target_audience": document.target_audience,
            "content_type": document.content_type,
            "topic": document.topic,
            "summary": document.summary,
            "chunk_count": len(document.knowledge_chunks or []),
        }

    @staticmethod
    def get_primary_knowledge_document(material: MaterialItem) -> Optional[KnowledgeDocument]:
        documents = sorted(material.knowledge_documents or [], key=lambda item: item.id)
        if not documents:
            return None
        return documents[0]

    @staticmethod
    def update_inbox_status(
        db: Session,
        owner_id: int,
        inbox_id: int,
        target_status: str,
        review_note: Optional[str] = None,
    ) -> dict[str, Any]:
        item = AcquisitionIntakeService.get_inbox_item(db, owner_id, inbox_id)
        if item is None:
            raise ValueError("收件箱内容不存在")

        current_status = str(item.status or "pending")
        if target_status not in AcquisitionIntakeService._STATUS_TRANSITIONS:
            raise ValueError("无效状态，仅支持 pending/review/discard")
        if target_status != current_status and target_status not in AcquisitionIntakeService._STATUS_TRANSITIONS[current_status]:
            raise ValueError(f"不允许从 {current_status} 流转到 {target_status}")

        item.status = target_status
        if review_note is not None:
            item.review_note = review_note
        db.commit()
        db.refresh(item)
        return {
            "inbox_id": int(item.id),
            "material_id": int(item.id),
            "status": str(item.status),
            "review_note": item.review_note,
        }

    @staticmethod
    def _apply_structure_filter(
        query,
        platform: str,
        account_type: str,
        target_audience: str,
    ):
        query = query.filter(KnowledgeDocument.platform == platform)
        query = query.filter(KnowledgeDocument.account_type == account_type)
        query = query.filter(KnowledgeDocument.target_audience == target_audience)
        return query

    @staticmethod
    def _keyword_score(query_tokens: list[str], document: KnowledgeDocument) -> float:
        doc_text = f"{document.title or ''} {document.summary or ''} {document.content_text or ''}"
        return float(sum(1 for token in query_tokens if token and token in doc_text))

    @staticmethod
    def _semantic_score(query_text: str, document: KnowledgeDocument) -> float:
        doc_text = f"{document.title or ''}\n{document.summary or ''}\n{document.content_text or ''}"
        if not query_text or not doc_text:
            return 0.0
        token_set_query = set(AcquisitionIntakeService._tokenize(query_text))
        token_set_doc = set(AcquisitionIntakeService._tokenize(doc_text))
        overlap = 0.0
        if token_set_query and token_set_doc:
            overlap = len(token_set_query & token_set_doc) / max(len(token_set_query | token_set_doc), 1)
        seq_ratio = SequenceMatcher(None, query_text[:500], doc_text[:500]).ratio()
        return round((overlap * 0.7) + (seq_ratio * 0.3), 4)

    @staticmethod
    def retrieve(
        db: Session,
        owner_id: int,
        query_text: str,
        platform: str,
        account_type: str,
        target_audience: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        base_query = db.query(KnowledgeDocument).filter(KnowledgeDocument.owner_id == owner_id)
        filtered_query = AcquisitionIntakeService._apply_structure_filter(base_query, platform, account_type, target_audience)
        candidates = filtered_query.order_by(desc(KnowledgeDocument.id)).limit(100).all()

        if not candidates:
            candidates = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.owner_id == owner_id, KnowledgeDocument.platform == platform)
                .order_by(desc(KnowledgeDocument.id))
                .limit(100)
                .all()
            )

        query_tokens = AcquisitionIntakeService._extract_keywords(query_text, limit=12)
        ranked: list[dict[str, Any]] = []
        for document in candidates:
            keyword_score = AcquisitionIntakeService._keyword_score(query_tokens, document)
            semantic_score = AcquisitionIntakeService._semantic_score(query_text, document)
            material = document.material_item
            hot_boost = 1.0 if material and material.hot_level == "high" else 0.5 if material and material.hot_level == "medium" else 0.0
            lead_boost = 1.0 if material and material.lead_level == "high" else 0.5 if material and material.lead_level == "medium" else 0.0
            final_score = round((keyword_score * 2.0) + (semantic_score * 10.0) + hot_boost + lead_boost, 4)
            chunks = sorted(document.knowledge_chunks or [], key=lambda item: item.chunk_index)[:3]
            ranked.append(
                {
                    "document_id": document.id,
                    "material_item_id": document.material_item_id,
                    "title": document.title,
                    "summary": document.summary,
                    "topic": document.topic,
                    "account_type": document.account_type,
                    "target_audience": document.target_audience,
                    "content_type": document.content_type,
                    "keyword_score": keyword_score,
                    "semantic_score": semantic_score,
                    "score": final_score,
                    "chunks": [chunk.chunk_text for chunk in chunks],
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    @staticmethod
    def _load_rules(
        db: Session,
        owner_id: int,
        platform: str,
        account_type: str,
        target_audience: str,
    ) -> list[Rule]:
        query = db.query(Rule).filter(Rule.owner_id == owner_id)
        query = query.filter((Rule.platform == platform) | (Rule.platform.is_(None)))
        query = query.filter((Rule.account_type == account_type) | (Rule.account_type.is_(None)))
        query = query.filter((Rule.target_audience == target_audience) | (Rule.target_audience.is_(None)))
        rules = query.order_by(desc(Rule.priority), desc(Rule.id)).limit(20).all()
        if rules:
            return rules

        default_rules = [
            Rule(
                owner_id=owner_id,
                rule_type="platform_rule",
                platform=platform,
                account_type=account_type,
                target_audience=target_audience,
                name="禁止违规承诺",
                content="不得使用包过、百分百下款、绝对化收益、虚假资质背书等表达。",
                priority=100,
            ),
            Rule(
                owner_id=owner_id,
                rule_type="structure_rule",
                platform=platform,
                account_type=account_type,
                target_audience=target_audience,
                name="三段式输出",
                content="默认使用开场钩子、痛点展开、行动引导三段式结构，不要堆砌空话。",
                priority=90,
            ),
        ]
        db.add_all(default_rules)
        db.flush()
        return default_rules

    @staticmethod
    def _select_prompt_template(
        db: Session,
        owner_id: int,
        task_type: str,
        platform: str,
        account_type: str,
        target_audience: str,
    ) -> Optional[PromptTemplate]:
        query = db.query(PromptTemplate).filter(
            PromptTemplate.owner_id == owner_id,
            PromptTemplate.task_type == task_type,
        )
        query = query.filter((PromptTemplate.platform == platform) | (PromptTemplate.platform.is_(None)))
        query = query.filter((PromptTemplate.account_type == account_type) | (PromptTemplate.account_type.is_(None)))
        query = query.filter((PromptTemplate.target_audience == target_audience) | (PromptTemplate.target_audience.is_(None)))
        template = query.order_by(desc(PromptTemplate.id)).first()
        if template is not None:
            return template

        template = PromptTemplate(
            owner_id=owner_id,
            task_type=task_type,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            version="v1",
            system_prompt="你是内容生成助手，负责基于素材和知识库生成可发布文案，必须遵守业务规则，不得抄袭参考原文。",
            user_prompt_template=(
                "请基于以下素材生成一篇{task_type}文案。目标平台:{platform}；账号类型:{account_type}；目标人群:{target_audience}。"
                "输出要求：贴近业务、结构清晰、避免空泛表达、不能直接复述参考素材。"
            ),
        )
        db.add(template)
        db.flush()
        return template

    @staticmethod
    async def generate(
        db: Session,
        owner_id: int,
        material_id: int,
        platform: str,
        account_type: str,
        target_audience: str,
        task_type: str,
        ai_service,
    ) -> dict[str, Any]:
        material = AcquisitionIntakeService.get_inbox_item(db, owner_id, material_id)
        if material is None:
            raise ValueError("素材不存在")

        references = AcquisitionIntakeService.retrieve(
            db=db,
            owner_id=owner_id,
            query_text=material.content_text or material.title or "",
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            limit=5,
        )
        rules = AcquisitionIntakeService._load_rules(db, owner_id, platform, account_type, target_audience)
        template = AcquisitionIntakeService._select_prompt_template(db, owner_id, task_type, platform, account_type, target_audience)

        reference_lines = []
        for ref in references:
            chunk_text = "\n".join(ref["chunks"][:2])
            reference_lines.append(
                f"- 标题: {ref['title'] or '无标题'}\n  主题: {ref['topic'] or '未分类'}\n  摘要: {ref['summary'] or ''}\n  参考片段: {chunk_text}"
            )

        rule_lines = [f"- {rule.name}: {rule.content}" for rule in rules]
        system_prompt = template.system_prompt if template else "你是内容生成助手，负责基于素材和知识库生成可发布文案。"
        user_prompt = template.user_prompt_template if template else (
            "请基于以下素材生成一篇{task_type}文案。目标平台:{platform}；账号类型:{account_type}；目标人群:{target_audience}。"
            "必须吸收参考知识的结构和洞察，但不能直接复制原文。输出只返回最终文案。"
        )
        prompt_body = user_prompt.format(
            task_type=task_type,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
        )
        final_prompt = (
            f"{prompt_body}\n\n"
            f"【原始素材】\n标题: {material.title or '无标题'}\n正文:\n{material.content_text or ''}\n\n"
            f"【素材属性】\n热度: {material.hot_level}\n线索等级: {material.lead_level}\n线索原因: {material.lead_reason or '无'}\n\n"
            f"【知识参考】\n{chr(10).join(reference_lines) if reference_lines else '无匹配知识'}\n\n"
            f"【规则约束】\n{chr(10).join(rule_lines) if rule_lines else '无附加规则'}"
        )

        output_text = await ai_service.call_llm(
            prompt=final_prompt,
            system_prompt=system_prompt,
            user_id=owner_id,
            scene=f"generation_{task_type}",
        )

        generation = GenerationTask(
            owner_id=owner_id,
            material_item_id=material.id,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            task_type=task_type,
            prompt_snapshot=final_prompt,
            output_text=output_text,
            reference_document_ids=[ref["document_id"] for ref in references],
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)

        return {
            "generation_task_id": generation.id,
            "material_id": material.id,
            "platform": platform,
            "account_type": account_type,
            "target_audience": target_audience,
            "task_type": task_type,
            "output_text": output_text,
            "references": references,
        }