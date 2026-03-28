import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin
from uuid import uuid4

from playwright.sync_api import Page

from app.collector.adapters.base import BaseCollector
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem
from app.collector.services.enricher import enrich_item, should_drop
from app.collector.services.normalizer import build_item
from app.utils.browser import create_browser


class XiaohongshuCollector(BaseCollector):
    BASE_URL = "https://www.xiaohongshu.com"
    SEARCH_URL = "https://www.xiaohongshu.com/search_result"

    def __init__(self) -> None:
        root_dir = Path(__file__).resolve().parents[2]
        self._artifacts_dir = root_dir / "artifacts"
        self._screenshots_dir = self._artifacts_dir / "screenshots"
        self._html_dir = self._artifacts_dir / "html"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._html_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, req: CollectRequest) -> tuple[list[ContentItem], CollectStats]:
        task_id = f"collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        stats = CollectStats()
        items: list[ContentItem] = []
        seeds: list[dict] = []
        seen_keys: set[str] = set()

        playwright, browser, context, page = create_browser()
        page.set_default_timeout(req.timeout_sec * 1000)
        try:
            search_url = f"{self.SEARCH_URL}?keyword={quote(req.keyword)}&source=web_search_result_notes&type=51"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            scroll_round = 0
            max_scroll_round = 12
            while len(seeds) < req.max_items and scroll_round < max_scroll_round:
                for card in page.locator("section").all():
                    raw = self._parse_list_card(card)
                    if not raw:
                        continue

                    stats.discovered += 1
                    dedup_key = f"{raw.get('source_id') or raw.get('url')}"
                    if req.dedup and dedup_key in seen_keys:
                        continue

                    seen_keys.add(dedup_key)
                    seeds.append(raw)
                    if len(seeds) >= req.max_items:
                        break

                if len(seeds) >= req.max_items:
                    break

                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1800)
                scroll_round += 1

            for raw in seeds:
                item = build_item(raw=raw, keyword=req.keyword, task_id=task_id)
                stats.list_success += 1

                if req.need_detail:
                    item.detail_attempted = True
                    item.parse_stage = "detail"
                    stats.detail_attempted += 1
                    try:
                        detail_data = self._fetch_detail_data(page, item.url, req.need_comments)
                        merged = item.model_dump()
                        merged.update(detail_data)
                        merged["parse_stage"] = "detail"
                        merged["parse_status"] = "detail_success" if self._is_detail_success(merged) else "detail_failed"
                        item = ContentItem(**merged)
                        if item.parse_status == "detail_success":
                            stats.detail_success += 1
                        else:
                            stats.detail_failed += 1
                    except Exception as ex:
                        item.parse_status = "detail_failed"
                        item.detail_error = str(ex)
                        stats.detail_failed += 1

                item = enrich_item(item)

                if should_drop(item):
                    item.parse_status = "dropped"
                    stats.dropped += 1

                items.append(item)

            return items, stats
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        task_id = f"collect_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        url = req.url or self._build_detail_url(req.source_id or "")
        source_id = req.source_id or self._extract_source_id(url)
        item = build_item(
            raw={
                "source_platform": req.platform,
                "source_id": source_id,
                "url": url,
                "parse_stage": "detail",
                "parse_status": "detail_failed",
                "detail_attempted": True,
            },
            keyword="",
            task_id=task_id,
        )

        if not url:
            item.detail_error = "missing_detail_url"
            return enrich_item(item)

        playwright, browser, context, page = create_browser()
        try:
            detail_data = self._fetch_detail_data(page, url, need_comments=True)
            merged = item.model_dump()
            merged.update(detail_data)
            merged["parse_stage"] = "detail"
            merged["parse_status"] = "detail_success" if self._is_detail_success(merged) else "detail_failed"
            result = ContentItem(**merged)
            return enrich_item(result)
        except Exception as ex:
            item.parse_status = "detail_failed"
            item.detail_error = str(ex)
            return enrich_item(item)
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def _parse_list_card(self, card) -> dict | None:
        href = self._first_attr(card, 'a[href*="/explore/"]', "href")
        if not href:
            return None

        full_url = urljoin(self.BASE_URL, href)
        source_id = self._extract_source_id(full_url)
        title = self._first_text(card, [".title", 'a[href*="/explore/"]'])
        snippet = self._first_text(card, [".desc", ".note-text", ".title"])
        author_name = self._first_text(card, [".author .name", ".name", ".author"])
        like_text = self._first_text(card, [".like-wrapper .count", ".count", ".like"])
        cover_url = self._first_attr(card, "img", "src")

        if not title and not snippet:
            return None

        return {
            "source_platform": "xiaohongshu",
            "source_type": "note",
            "source_id": source_id,
            "url": full_url,
            "title": self._clean_text(title),
            "snippet": self._clean_text(snippet),
            "author_name": self._clean_text(author_name),
            "cover_url": self._normalize_url(cover_url),
            "like_count": self._to_int_count(like_text),
            "parse_stage": "list",
            "parse_status": "list_only",
            "raw_data": {"stage": "list", "href": href},
        }

    def _fetch_detail_data(self, page: Page, url: str, need_comments: bool) -> dict:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        title = self._first_text(page, ["h1", "#detail-title", ".note-title"])
        content_text = self._first_text(page, ["#detail-desc", ".note-content", "article"])
        author_name = self._first_text(page, [".author-container .name", ".author .name", ".username"])
        publish_time = self._extract_publish_time(page)
        image_urls = self._extract_content_image_urls(page)

        like_count = self._extract_metric_by_selectors(page, "点赞")
        comment_count = self._extract_metric_by_selectors(page, "评论") if need_comments else None

        return {
            "title": self._clean_text(title),
            "content_text": self._clean_text(content_text),
            "snippet": self._clean_text(content_text)[:100] if content_text else "",
            "author_name": self._clean_text(author_name),
            "publish_time": publish_time,
            "image_urls": image_urls,
            "image_count": len(image_urls),
            "like_count": like_count,
            "comment_count": comment_count,
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {"stage": "detail"},
        }

    def _is_detail_success(self, item: dict) -> bool:
        content_text = (item.get("content_text") or "").strip()
        return bool(content_text) and (
            item.get("publish_time") is not None
            or (item.get("image_count") or 0) > 0
            or item.get("comment_count") is not None
        )

    def _extract_publish_time(self, page: Page) -> str | None:
        selectors = ["time", "[class*=publish]", "[class*=time]", "[data-testid*=time]"]
        for selector in selectors:
            text = self._first_text(page, [selector])
            parsed = self._parse_datetime_text(text)
            if parsed:
                return parsed

        html = page.content()
        match = re.search(
            r"(20\\d{2})[-/.](\\d{1,2})[-/.](\\d{1,2})(?:\\s+|T)(\\d{1,2}):(\\d{1,2})(?::(\\d{1,2}))?",
            html,
        )
        if not match:
            return None

        year, month, day, hour, minute, second = match.groups()
        try:
            parsed = datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second or 0),
            ).astimezone()
            return parsed.isoformat()
        except ValueError:
            return None

    def _extract_metric_by_selectors(self, page: Page, label: str) -> int | None:
        selectors = [
            f"[aria-label*='{label}']",
            f"[title*='{label}']",
            f"button:has-text('{label}')",
            f"span:has-text('{label}')",
            f"div:has-text('{label}')",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() <= 0:
                continue
            text = self._clean_text(locator.first.inner_text(timeout=800))
            if not text:
                continue
            number = self._extract_count_from_text(text)
            if number is not None:
                return number
        return None

    def _extract_content_image_urls(self, page: Page) -> list[str]:
        urls: list[str] = []
        selectors = [
            ".note-content img",
            "article img",
            "[class*=note] [class*=content] img",
            "[class*=desc] img",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            if count <= 0:
                continue
            for idx in range(count):
                img = locator.nth(idx)
                src = img.get_attribute("src") or img.get_attribute("data-src")
                normalized = self._normalize_url(src)
                if not normalized:
                    continue
                if self._is_noise_image(normalized):
                    continue
                urls.append(normalized)

        deduped: list[str] = []
        seen: set[str] = set()
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            deduped.append(url)
        return deduped[:9]

    def _first_text(self, scope, selectors: list[str]) -> str:
        for selector in selectors:
            locator = scope.locator(selector)
            if locator.count() <= 0:
                continue
            value = (locator.first.inner_text(timeout=500) or "").strip()
            if value:
                return value
        return ""

    def _first_attr(self, scope, selector: str, attr: str) -> str:
        locator = scope.locator(selector)
        if locator.count() <= 0:
            return ""
        value = locator.first.get_attribute(attr)
        return (value or "").strip()

    def _to_int_count(self, text: str | None) -> int:
        if not text:
            return 0
        normalized = text.replace(",", "").replace(" ", "").lower().replace("w", "万")
        try:
            if normalized.endswith("万"):
                return int(float(normalized[:-1]) * 10000)
            return int(float(normalized))
        except Exception:
            return 0

    def _extract_count_from_text(self, text: str) -> int | None:
        match = re.search(r"(\d+(?:\.\d+)?(?:万|w|W)?)", text)
        if not match:
            return None
        return self._to_int_count(match.group(1))

    def _extract_source_id(self, url: str) -> str:
        if not url:
            return ""
        return url.rstrip("/").split("/")[-1]

    def _build_detail_url(self, source_id: str) -> str:
        if not source_id:
            return ""
        return f"{self.BASE_URL}/explore/{source_id}"

    def _clean_text(self, text: str | None) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _normalize_url(self, url: str | None) -> str | None:
        if not url:
            return None
        text = url.strip()
        if not text or text.startswith("data:"):
            return None
        match = re.match(r"^(https?://[^?#]+)", text)
        if not match:
            return None
        return match.group(1)

    def _is_noise_image(self, url: str) -> bool:
        lowered = url.lower()
        noise_keywords = [
            "avatar",
            "icon",
            "logo",
            "emoji",
            "badge",
            "profile",
            "fe-platform",
            "picasso-static",
        ]
        return any(keyword in lowered for keyword in noise_keywords)

    def _parse_datetime_text(self, text: str) -> str | None:
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        exact_match = re.search(
            r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
            cleaned,
        )
        if exact_match:
            year, month, day, hour, minute, second = exact_match.groups()
            try:
                return datetime(
                    int(year),
                    int(month),
                    int(day),
                    int(hour),
                    int(minute),
                    int(second or 0),
                ).astimezone().isoformat()
            except ValueError:
                return None

        date_only_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
        if not date_only_match:
            return None

        year, month, day = date_only_match.groups()
        try:
            return datetime(int(year), int(month), int(day), 0, 0, 0).astimezone().isoformat()
        except ValueError:
            return None
