from datetime import datetime

from app.schemas.result import ContentItem
from app.services.scoring import (
    calc_engagement_score,
    calc_field_completeness,
    calc_lead_score,
    calc_quality_score,
    detect_contact_hint,
)


def enrich_item(item: ContentItem) -> ContentItem:
    data = item.model_dump()
    data["content_length"] = len((data.get("content_text") or "").strip())
    data["image_count"] = len(data.get("image_urls") or [])

    data["field_completeness"] = calc_field_completeness(data)
    data["engagement_score"] = calc_engagement_score(data)
    data["quality_score"] = calc_quality_score(data)
    data["lead_score"] = calc_lead_score(data)

    full_text = f"{data.get('title', '')}\n{data.get('content_text', '')}"
    data["has_contact_hint"] = detect_contact_hint(full_text)

    data["is_detail_complete"] = bool((data.get("content_text") or "").strip()) and (
        data.get("publish_time") is not None
        or (data.get("image_count") or 0) > 0
        or data.get("comment_count") is not None
    )

    if data.get("parse_status") == "detail_failed":
        data["risk_level"] = "medium"
        data["risk_reason"] = data.get("detail_error") or "detail_failed"
    elif not data.get("url"):
        data["risk_level"] = "high"
        data["risk_reason"] = "missing_url"
    elif (data.get("field_completeness") or 0) < 0.4:
        data["risk_level"] = "medium"
        data["risk_reason"] = "low_completeness"
    else:
        data["risk_level"] = "low"
        data["risk_reason"] = ""

    data["updated_at"] = datetime.now(item.updated_at.tzinfo) if item.updated_at.tzinfo else datetime.now()
    return ContentItem(**data)


def should_drop(item: ContentItem) -> bool:
    title = (item.title or "").strip()
    content_text = (item.content_text or "").strip()
    url = (item.url or "").strip()

    if not url:
        item.drop_reason = "missing_url"
        return True

    if not title and not content_text:
        item.drop_reason = "missing_title_and_content"
        return True

    return False
