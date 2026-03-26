import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

from playwright.sync_api import Page

from app.collectors.base import BaseCollector
from app.normalizers.content_normalizer import ContentNormalizer
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem, RiskStatus
from app.utils.browser import create_browser


class XiaohongshuCollector(BaseCollector):
    BASE_URL = "https://www.xiaohongshu.com"
    SEARCH_URL = "https://www.xiaohongshu.com/search_result"

    def __init__(self) -> None:
        self._normalizer = ContentNormalizer()
        root_dir = Path(__file__).resolve().parents[2]
        self._artifacts_dir = root_dir / "artifacts"
        self._screenshots_dir = self._artifacts_dir / "screenshots"
        self._html_dir = self._artifacts_dir / "html"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._html_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, req: CollectRequest) -> tuple[list[ContentItem], CollectStats]:
        playwright, browser, context, page = create_browser()
        page.set_default_timeout(req.timeout_sec * 1000)

        stats = CollectStats()
        items: list[ContentItem] = []
        seen_keys: set[str] = set()

        search_url = f"{self.SEARCH_URL}?keyword={quote(req.keyword)}&source=web_search_result_notes&type=51"
        try:
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            scroll_round = 0
            max_scroll_round = 12

            while len(items) < req.max_items and scroll_round < max_scroll_round:
                cards = page.locator("section").all()
                for card in cards:
                    seed = self._parse_list_card(card, req.keyword)
                    if not seed:
                        stats.parse_failed += 1
                        continue

                    stats.discovered += 1
                    dedup_key = f"{seed.platform}:{seed.source_id or seed.url}"
                    if req.dedup and dedup_key in seen_keys:
                        stats.deduplicated += 1
                        continue

                    seen_keys.add(dedup_key)
                    items.append(seed)
                    if len(items) >= req.max_items:
                        break

                if len(items) >= req.max_items:
                    break

                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1800)
                scroll_round += 1

            if req.need_detail:
                for idx, item in enumerate(items):
                    stats.detail_attempted += 1
                    detail_item = self._enrich_detail(page, item, req.need_comments)
                    items[idx] = detail_item
                    if detail_item.parse_status == "detail_success":
                        stats.detail_success += 1
                    elif detail_item.parse_status == "risk_blocked":
                        stats.risk_blocked += 1
                    elif detail_item.parse_status in ("detail_failed", "parse_failed"):
                        stats.parse_failed += 1

            return items, stats
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        url = req.url or self._build_detail_url(req.source_id or "")
        source_id = req.source_id or self._extract_source_id(url)
        now = datetime.now().astimezone()
        item = ContentItem(
            platform="xiaohongshu",
            keyword=None,
            source_id=source_id,
            url=url,
            collected_at=now,
            parse_status="detail_failed",
            risk_status="normal",
        )

        if not url:
            item.parse_status = "parse_failed"
            item.raw_data["error"] = "缺少详情页地址"
            return item

        playwright, browser, context, page = create_browser()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            return self._enrich_detail(page, item, need_comments=True)
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def _parse_list_card(self, card, keyword: str) -> Optional[ContentItem]:
        href = self._first_attr(card, 'a[href*="/explore/"]', "href")
        if not href:
            return None

        full_url = urljoin(self.BASE_URL, href)
        source_id = self._extract_source_id(full_url)
        title = self._first_text(card, [".title", 'a[href*="/explore/"]'])
        author_name = self._first_text(card, [".author .name", ".name", ".author"])
        like_text = self._first_text(card, [".like-wrapper .count", ".count", ".like"])
        snippet = self._first_text(card, [".desc", ".note-text", ".title"])
        cover_url = self._first_attr(card, "img", "src")

        if not title and not snippet:
            return None

        like_count = self._to_int_count(like_text)
        now = datetime.now().astimezone()
        item = ContentItem(
            platform="xiaohongshu",
            keyword=keyword,
            source_id=source_id,
            url=full_url,
            title=self._clean_text(title) or None,
            author_name=self._clean_text(author_name) or None,
            snippet=self._clean_text(snippet) or None,
            cover_url=cover_url or None,
            content_image_urls=[],
            like_count=like_count,
            comment_count=None,
            publish_time=None,
            collected_at=now,
            parse_status="list_only",
            risk_status="normal",
            field_source={
                "title": "list_dom",
                "snippet": "list_dom",
                "author_name": "list_dom",
                "cover_url": "list_dom",
                "like_count": "list_dom",
            },
            raw_data={"stage": "list", "href": href},
        )
        return self._normalizer.normalize(item)

    def _enrich_detail(self, page: Page, item: ContentItem, need_comments: bool) -> ContentItem:
        try:
            page.goto(item.url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            risk = self._detect_risk(page)
            if risk != "normal":
                item.parse_status = "risk_blocked"
                item.risk_status = risk
                screenshot, html_file = self._dump_failure_artifacts(page, item.source_id or "unknown", "risk")
                item.raw_data.update({"stage": "detail", "screenshot": screenshot, "html_dump": html_file})
                return item

            title = self._first_text(page, ["h1", "#detail-title", ".note-title"])
            content_text = self._first_text(page, ["#detail-desc", ".note-content", "article"])
            author_name = self._first_text(page, [".author-container .name", ".author .name", ".username"])
            publish_time, publish_time_source = self._extract_publish_time(page)
            content_image_urls = self._extract_content_image_urls(page)
            author_avatar_url = self._extract_author_avatar_url(page)
            like_count = self._extract_metric_by_selectors(page, "点赞")
            comment_count = self._extract_metric_by_selectors(page, "评论") if need_comments else item.comment_count

            merged_title = self._clean_text(title) or item.title
            merged_content = self._clean_text(content_text)
            merged_snippet = item.snippet
            if not merged_snippet and merged_content:
                merged_snippet = merged_content[:100]

            item.title = merged_title
            item.author_name = self._clean_text(author_name) or item.author_name
            item.content_text = merged_content or item.content_text
            item.snippet = merged_snippet
            item.content_image_urls = content_image_urls
            item.cover_url = content_image_urls[0] if content_image_urls else item.cover_url
            item.author_avatar_url = author_avatar_url or item.author_avatar_url
            item.like_count = like_count if like_count is not None else item.like_count
            item.comment_count = comment_count
            item.publish_time = publish_time
            item.risk_status = "normal"
            item.field_source.update(
                {
                    "title": "detail_dom",
                    "author_name": "detail_dom",
                    "content_text": "detail_dom",
                    "content_image_urls": "detail_dom",
                    "cover_url": "detail_dom",
                    "author_avatar_url": "detail_dom",
                    "like_count": "detail_dom",
                }
            )
            if need_comments:
                item.field_source["comment_count"] = "detail_dom"
            if publish_time_source:
                item.field_source["publish_time"] = publish_time_source

            has_detail = bool(item.content_text) and bool(item.title)
            item.parse_status = "detail_success" if has_detail else "detail_failed"
            item.raw_data.update({"stage": "detail"})
            return self._normalizer.normalize(item)
        except Exception as ex:
            item.parse_status = "detail_failed"
            item.risk_status = "normal"
            screenshot, html_file = self._dump_failure_artifacts(page, item.source_id or "unknown", "error")
            item.raw_data.update(
                {
                    "stage": "detail",
                    "error": str(ex),
                    "screenshot": screenshot,
                    "html_dump": html_file,
                }
            )
            return item

    def _extract_publish_time(self, page: Page) -> tuple[Optional[datetime], str]:
        selectors = [
            "time",
            "[class*=publish]",
            "[class*=time]",
            "[data-testid*=time]",
        ]
        for selector in selectors:
            text = self._first_text(page, [selector])
            parsed = self._parse_datetime_text(text)
            if parsed:
                return parsed, "detail_dom"

        html = page.content()
        match = re.search(
            r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
            html,
        )
        if match:
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
                return parsed, "detail_script"
            except ValueError:
                return None, ""

        return None, ""

    def _extract_metric_by_selectors(self, page: Page, label: str) -> Optional[int]:
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

    def _extract_author_avatar_url(self, page: Page) -> Optional[str]:
        selectors = [
            ".author img",
            "[class*=author] [class*=avatar] img",
            "img[class*=avatar]",
        ]
        for selector in selectors:
            url = self._first_attr(page, selector, "src")
            normalized = self._normalize_url(url)
            if normalized:
                return normalized
        return None

    def _detect_risk(self, page: Page) -> RiskStatus:
        text = self._clean_text(page.locator("body").inner_text(timeout=1200))
        if not text:
            return "blocked"
        if "请先登录" in text or "登录后" in text:
            return "login_required"
        if "验证码" in text or "安全验证" in text:
            return "captcha"
        if "访问受限" in text or "异常请求" in text or "请求过于频繁" in text:
            return "blocked"
        return "normal"

    def _dump_failure_artifacts(self, page: Page, source_id: str, tag: str) -> tuple[str, str]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"xhs_{source_id}_{tag}_{stamp}"
        screenshot = self._screenshots_dir / f"{base}.png"
        html_file = self._html_dir / f"{base}.html"

        try:
            page.screenshot(path=str(screenshot), full_page=True)
        except Exception:
            pass

        try:
            html_file.write_text(page.content(), encoding="utf-8")
        except Exception:
            pass

        return str(screenshot), str(html_file)

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

    def _to_int_count(self, text: Optional[str]) -> int:
        if not text:
            return 0
        normalized = text.replace(",", "").replace(" ", "").lower().replace("w", "万")
        try:
            if normalized.endswith("万"):
                return int(float(normalized[:-1]) * 10000)
            return int(float(normalized))
        except Exception:
            return 0

    def _extract_count_from_text(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+(?:\.\d+)?(?:万|w|W)?)", text)
        if not match:
            return None
        value = self._to_int_count(match.group(1))
        return value

    def _extract_source_id(self, url: str) -> str:
        if not url:
            return ""
        return url.rstrip("/").split("/")[-1]

    def _build_detail_url(self, source_id: str) -> str:
        if not source_id:
            return ""
        return f"{self.BASE_URL}/explore/{source_id}"

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        text = url.strip()
        if not text or text.startswith("data:"):
            return None
        # Keep canonical image path and drop query to avoid duplicate variants.
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

    def _parse_datetime_text(self, text: str) -> Optional[datetime]:
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
                ).astimezone()
            except ValueError:
                return None

        date_only_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
        if not date_only_match:
            return None
        year, month, day = date_only_match.groups()
        try:
            return datetime(int(year), int(month), int(day), 0, 0, 0).astimezone()
        except ValueError:
            return None

    def _compute_quality(self, title: str, snippet: str, content_text: str, image_count: int) -> float:
        score = 0.0
        if len(title) >= 8:
            score += 25
        if len(snippet) >= 20:
            score += 20
        if len(content_text) >= 80:
            score += 35
        if image_count > 0:
            score += 20
        return min(score, 100.0)