import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

from playwright.sync_api import Page

from app.collectors.base import BaseCollector
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem
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
            image_urls=[cover_url] if cover_url else [],
            like_count=like_count,
            comment_count=None,
            publish_time=None,
            collected_at=now,
            parse_status="list_only",
            risk_status="normal",
            engagement_score=float(like_count),
            quality_score=self._compute_quality(
                title=self._clean_text(title),
                snippet=self._clean_text(snippet),
                content_text="",
                image_count=1 if cover_url else 0,
            ),
            raw_data={"stage": "list", "href": href},
        )
        return item

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
            publish_time = self._extract_publish_time(page)
            image_urls = self._extract_image_urls(page)
            like_count = self._extract_metric(page, "点赞")
            comment_count = self._extract_metric(page, "评论") if need_comments else item.comment_count

            merged_title = self._clean_text(title) or item.title
            merged_content = self._clean_text(content_text)
            merged_snippet = (merged_content[:180] if merged_content else item.snippet) or None

            item.title = merged_title
            item.author_name = self._clean_text(author_name) or item.author_name
            item.content_text = merged_content or item.content_text
            item.snippet = merged_snippet
            item.image_urls = image_urls
            item.cover_url = image_urls[0] if image_urls else item.cover_url
            item.like_count = like_count if like_count is not None else item.like_count
            item.comment_count = comment_count
            item.publish_time = publish_time
            item.risk_status = "normal"

            has_detail = bool(item.content_text) and bool(item.title)
            item.parse_status = "detail_success" if has_detail else "detail_failed"
            item.engagement_score = float((item.like_count or 0) + (item.comment_count or 0) * 3)
            item.quality_score = self._compute_quality(
                title=item.title or "",
                snippet=item.snippet or "",
                content_text=item.content_text or "",
                image_count=len(item.image_urls),
            )
            item.raw_data.update({"stage": "detail"})
            return item
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

    def _extract_publish_time(self, page: Page) -> Optional[datetime]:
        text = self._clean_text(page.locator("body").inner_text(timeout=1200))
        if not text:
            return None

        match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2}))?", text)
        if not match:
            return None

        year, month, day, hour, minute = match.groups()
        hh = int(hour) if hour else 0
        mm = int(minute) if minute else 0
        try:
            return datetime(int(year), int(month), int(day), hh, mm).astimezone()
        except ValueError:
            return None

    def _extract_metric(self, page: Page, label: str) -> Optional[int]:
        text = self._clean_text(page.locator("body").inner_text(timeout=1200))
        if not text:
            return None

        pattern = rf"{label}\s*(\d+(?:\.\d+)?[万wW]?)"
        match = re.search(pattern, text)
        if not match:
            return None
        return self._to_int_count(match.group(1))

    def _extract_image_urls(self, page: Page) -> list[str]:
        urls: list[str] = []
        for img in page.locator("img").all():
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if not src or src.startswith("data:"):
                continue
            urls.append(src)
        return list(dict.fromkeys(urls))[:20]

    def _detect_risk(self, page: Page) -> str:
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