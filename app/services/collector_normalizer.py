import re
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from app.schemas.result import ContentItem, ParseStage, ParseStatus


CST = timezone(timedelta(hours=8))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u200b", "").strip()
    return re.sub(r"\s+", " ", text)


def normalize_snippet(title: str, snippet: str) -> str:
    clean_title = normalize_text(title)
    clean_snippet = normalize_text(snippet)
    if not clean_snippet:
        return ""
    if clean_snippet == clean_title:
        return ""
    return clean_snippet


def normalize_parse_stage(value: Any) -> ParseStage:
    stage = normalize_text(value)
    return cast(ParseStage, stage) if stage in {"list", "detail"} else "list"


def normalize_parse_status(value: Any) -> ParseStatus:
    status = normalize_text(value)
    return cast(ParseStatus, status) if status in {"list_only", "detail_success", "detail_failed", "dropped"} else "list_only"


def normalize_image_urls(image_urls: Any) -> list[str]:
    if not image_urls:
        return []

    if isinstance(image_urls, str):
        image_urls = [x.strip() for x in image_urls.splitlines() if x.strip()]

    if not isinstance(image_urls, list):
        return []

    clean_urls: list[str] = []
    seen: set[str] = set()
    for value in image_urls:
        url = normalize_text(value)
        if not url:
            continue
        if url.startswith("data:"):
            continue
        if url in seen:
            continue
        seen.add(url)
        clean_urls.append(url)
    return clean_urls


def normalize_tags(tags: Any) -> list[str]:
    if not tags:
        return []

    if isinstance(tags, str):
        tags = re.split(r"[,\n，#\s]+", tags)

    if not isinstance(tags, list):
        return []

    clean_tags: list[str] = []
    seen: set[str] = set()
    for value in tags:
        tag = normalize_text(value).strip("#")
        if not tag:
            continue
        if tag in seen:
            continue
        seen.add(tag)
        clean_tags.append(tag)
    return clean_tags


def normalize_number(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = normalize_text(value).lower().replace(",", "")
    try:
        if text.endswith("w") or text.endswith("万"):
            return int(float(text[:-1]) * 10000)
        if text.endswith("k"):
            return int(float(text[:-1]) * 1000)
        return int(float(text))
    except Exception:
        return None


def parse_publish_time(value: Any) -> str | None:
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = normalize_text(value)
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return text

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt.isoformat()


def build_item(raw: dict[str, Any], keyword: str, task_id: str) -> ContentItem:
    title = normalize_text(raw.get("title"))
    snippet = normalize_snippet(title, normalize_text(raw.get("snippet")))
    content_text = normalize_text(raw.get("content_text"))
    image_urls = normalize_image_urls(raw.get("image_urls"))

    now = datetime.now(CST)

    return ContentItem(
        source_platform=normalize_text(raw.get("source_platform")) or "xiaohongshu",
        source_type=normalize_text(raw.get("source_type")) or "note",
        source_id=normalize_text(raw.get("source_id")),
        url=normalize_text(raw.get("url")),
        keyword=normalize_text(keyword),
        task_id=normalize_text(task_id),
        title=title or None,
        snippet=snippet or None,
        cover_url=normalize_text(raw.get("cover_url")) or None,
        author_name=normalize_text(raw.get("author_name")) or None,
        author_id=normalize_text(raw.get("author_id")) or None,
        author_home_url=normalize_text(raw.get("author_home_url")) or None,
        like_count=normalize_number(raw.get("like_count")),
        content_text=content_text or None,
        image_urls=image_urls,
        image_count=len(image_urls),
        publish_time=parse_publish_time(raw.get("publish_time")),
        comment_count=normalize_number(raw.get("comment_count")),
        share_count=normalize_number(raw.get("share_count")),
        collect_count=normalize_number(raw.get("collect_count")),
        tags=normalize_tags(raw.get("tags")),
        parse_stage=normalize_parse_stage(raw.get("parse_stage")),
        parse_status=normalize_parse_status(raw.get("parse_status")),
        detail_attempted=bool(raw.get("detail_attempted", False)),
        detail_error=normalize_text(raw.get("detail_error")),
        drop_reason=normalize_text(raw.get("drop_reason")),
        content_length=len(content_text),
        collected_at=now,
        updated_at=now,
        raw_data=raw.get("raw_data") or {},
    )
