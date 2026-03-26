import re
from copy import deepcopy
from urllib.parse import urlsplit, urlunsplit

from app.schemas.result import ContentItem


class ContentNormalizer:
    BAD_IMAGE_KEYWORDS = (
        "avatar",
        "icon",
        "logo",
        "emoji",
        "badge",
        "profile",
        "fe-platform",
        "picasso-static",
    )

    def normalize(self, item: ContentItem) -> ContentItem:
        normalized = deepcopy(item)

        normalized.title = self._clean_text(normalized.title)
        normalized.author_name = self._clean_text(normalized.author_name)
        normalized.snippet = self._clean_text(normalized.snippet)
        normalized.content_text = self._clean_text(normalized.content_text)

        if normalized.content_text:
            normalized.content_preview = normalized.content_text[:120]

        if not normalized.snippet and normalized.content_text:
            normalized.snippet = normalized.content_text[:100]

        normalized.cover_url = self._normalize_url(normalized.cover_url)
        normalized.author_avatar_url = self._normalize_url(normalized.author_avatar_url)
        normalized.content_image_urls = self._filter_content_images(normalized.content_image_urls)

        if not normalized.cover_url and normalized.content_image_urls:
            normalized.cover_url = normalized.content_image_urls[0]

        normalized.data_quality = self._build_data_quality(normalized)
        normalized.quality_score = self._calc_quality_score(normalized)
        normalized.engagement_score = float((normalized.like_count or 0) + (normalized.comment_count or 0) * 3)
        return normalized

    def _build_data_quality(self, item: ContentItem) -> dict[str, object]:
        return {
            "has_title": bool(item.title),
            "has_snippet": bool(item.snippet),
            "has_content_text": bool(item.content_text),
            "has_publish_time": bool(item.publish_time),
            "has_cover_url": bool(item.cover_url),
            "content_image_count": len(item.content_image_urls or []),
            "has_like_count": item.like_count is not None,
            "has_comment_count": item.comment_count is not None,
        }

    def _calc_quality_score(self, item: ContentItem) -> float:
        score = 0.0
        if item.title:
            score += 0.15
        if item.snippet:
            score += 0.10
        if item.content_text:
            score += 0.25
        if item.publish_time:
            score += 0.15
        if item.cover_url:
            score += 0.10
        if item.content_image_urls:
            score += 0.10
        if item.like_count is not None:
            score += 0.10
        if item.comment_count is not None:
            score += 0.05
        return round(min(score, 1.0), 4)

    def _filter_content_images(self, urls: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw_url in urls or []:
            normalized_url = self._normalize_url(raw_url)
            if not normalized_url:
                continue
            lowered = normalized_url.lower()
            if any(keyword in lowered for keyword in self.BAD_IMAGE_KEYWORDS):
                continue
            if normalized_url in seen:
                continue
            seen.add(normalized_url)
            result.append(normalized_url)
        return result[:9]

    def _normalize_url(self, url: str | None) -> str | None:
        if not url:
            return None
        text = url.strip()
        if not text or text.startswith("data:"):
            return None
        parts = urlsplit(text)
        if not parts.scheme or not parts.netloc:
            return None
        # Strip query/fragment to deduplicate same image payload.
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _clean_text(self, text: str | None) -> str | None:
        if not text:
            return None
        normalized = text.replace("\u200b", " ").replace("\xa0", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized or None
