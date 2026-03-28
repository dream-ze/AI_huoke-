import re
from typing import Any


FIELD_WEIGHTS = {
    "title": 0.10,
    "url": 0.10,
    "author_name": 0.05,
    "like_count": 0.05,
    "content_text": 0.30,
    "publish_time": 0.10,
    "comment_count": 0.10,
    "image_urls": 0.10,
    "source_id": 0.10,
}


CONTACT_HINT_PATTERNS = [
    r"微信",
    r"\\bvx\\b",
    r"\\bvx[:：]?\\s*[a-zA-Z0-9_-]+",
    r"\\bv[:：]?\\s*[a-zA-Z0-9_-]{4,}",
    r"加我",
    r"私信",
    r"联系我",
    r"手机号",
    r"电话",
    r"咨询",
]


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def calc_field_completeness(item: dict[str, Any]) -> float:
    score = 0.0
    for field, weight in FIELD_WEIGHTS.items():
        if _is_non_empty(item.get(field)):
            score += weight
    return round(score, 4)


def calc_engagement_score(item: dict[str, Any]) -> float:
    like_count = item.get("like_count") or 0
    comment_count = item.get("comment_count") or 0
    collect_count = item.get("collect_count") or 0
    share_count = item.get("share_count") or 0

    score = like_count * 1.0 + comment_count * 3.0 + collect_count * 2.0 + share_count * 2.0
    return round(score, 2)


def calc_quality_score(item: dict[str, Any]) -> float:
    score = 0.2

    title = (item.get("title") or "").strip()
    content_text = (item.get("content_text") or "").strip()
    content_length = len(content_text)
    image_count = item.get("image_count") or 0
    field_completeness = item.get("field_completeness") or 0

    if title:
        score += 0.10
    if content_length >= 50:
        score += 0.20
    if content_length >= 150:
        score += 0.15
    if item.get("publish_time"):
        score += 0.10
    if item.get("author_name"):
        score += 0.05
    if item.get("comment_count") is not None:
        score += 0.05
    if image_count > 0:
        score += 0.10
    if field_completeness >= 0.7:
        score += 0.10

    if not content_text:
        score -= 0.20
    if not item.get("url"):
        score -= 0.20

    return round(max(0.0, min(score, 1.0)), 4)


def detect_contact_hint(text: str) -> bool:
    if not text:
        return False
    for pattern in CONTACT_HINT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def calc_lead_score(item: dict[str, Any]) -> float:
    score = 0.0
    title = item.get("title") or ""
    content_text = item.get("content_text") or ""
    full_text = f"{title}\\n{content_text}"

    if (item.get("engagement_score") or 0) >= 100:
        score += 0.20
    if (item.get("quality_score") or 0) >= 0.60:
        score += 0.20
    if detect_contact_hint(full_text):
        score += 0.30
    if item.get("comment_count") not in (None, 0):
        score += 0.10
    if (item.get("field_completeness") or 0) >= 0.70:
        score += 0.20

    return round(min(score, 1.0), 4)
