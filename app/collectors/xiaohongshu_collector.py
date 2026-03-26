import re
from typing import Tuple
from urllib.parse import quote, urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.collectors.base import BaseCollector
from app.schemas.detail import CollectDetailRequest
from app.schemas.result import CollectStats, ContentItem, ContentMeta
from app.utils.browser import create_browser


class XiaohongshuCollector(BaseCollector):
    BASE_URL = "https://www.xiaohongshu.com"
    COLLECTOR_VERSION = "v1.0"

    def collect(self, keyword: str, max_items: int) -> Tuple[list[ContentItem], CollectStats, bool]:
        playwright, browser, context, page = create_browser()

        results: list[ContentItem] = []
        seen_urls: set[str] = set()
        seen_source_ids: set[str] = set()

        stats = CollectStats(scanned=0, parsed=0, deduplicated=0, failed=0)
        has_more = False

        search_url = (
            f"https://www.xiaohongshu.com/search_result"
            f"?keyword={quote(keyword)}&source=web_search_result_notes&type=51"
        )

        try:
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            scroll_round = 0
            max_scroll_round = 15

            while len(results) < max_items and scroll_round < max_scroll_round:
                cards = page.locator("section").all()

                for index, card in enumerate(cards, start=1):
                    stats.scanned += 1

                    try:
                        text = card.inner_text(timeout=2000).strip()
                        if not text:
                            stats.failed += 1
                            continue

                        href = self._extract_note_href(card)
                        if not href:
                            stats.failed += 1
                            continue

                        full_url = urljoin(self.BASE_URL, href)
                        source_id = self._extract_source_id(full_url)

                        if full_url in seen_urls or (source_id and source_id in seen_source_ids):
                            stats.deduplicated += 1
                            continue

                        cover_url = self._extract_cover_url(card)
                        title, author_name, like_count, comment_count, snippet = self._parse_card_text(text)

                        item = self._build_item(
                            keyword=keyword,
                            search_url=search_url,
                            full_url=full_url,
                            source_id=source_id,
                            title=title,
                            author_name=author_name,
                            snippet=snippet,
                            cover_url=cover_url,
                            like_count=like_count,
                            comment_count=comment_count,
                            raw_text=text,
                            href=href,
                            rank=len(results) + 1,
                            position=index,
                        )

                        results.append(item)
                        seen_urls.add(full_url)
                        if source_id:
                            seen_source_ids.add(source_id)
                        stats.parsed += 1

                        if len(results) >= max_items:
                            break

                    except Exception as ex:
                        stats.failed += 1
                        if len(results) >= max_items:
                            break
                        _ = ex
                        continue

                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(2500)
                scroll_round += 1

            if len(results) >= max_items:
                has_more = True

            return results, stats, has_more

        except PlaywrightTimeoutError:
            return results, stats, has_more

        except Exception:
            return results, stats, has_more

        finally:
            context.close()
            browser.close()
            playwright.stop()

    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        url = req.url or self._build_detail_url(req.source_id or "")
        source_id = req.source_id or self._extract_source_id(url)

        item = ContentItem(
            platform="xiaohongshu",
            keyword="",
            source_id=source_id,
            url=url,
            source_type="note",
        )

        if not url:
            item.parse_status = "failed"
            item.error_message = "缺少详情页地址"
            return item

        playwright, browser, context, page = create_browser()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)

            title = ""
            for selector in ["h1", "#detail-title", "[data-v-6f4f8f9f] h1"]:
                locator = page.locator(selector)
                if locator.count() > 0:
                    value = locator.first.inner_text(timeout=1000).strip()
                    if value:
                        title = value
                        break

            body_text = page.locator("body").inner_text(timeout=2000)
            snippet = self._build_snippet(body_text)
            image_urls = self._extract_image_urls(page)
            cover_url = image_urls[0] if image_urls else ""

            like_count = self._normalize_count(body_text, r"赞\s*(\d+(?:\.\d+)?[万wW]?)")
            comment_count = self._normalize_count(body_text, r"评论\s*(\d+(?:\.\d+)?[万wW]?)")
            collect_count = self._normalize_count(body_text, r"收藏\s*(\d+(?:\.\d+)?[万wW]?)")

            item.title = title[:200]
            item.author_name = ""
            item.snippet = snippet
            item.content_text = snippet
            item.cover_url = cover_url
            item.image_urls = image_urls
            item.like_count = like_count
            item.comment_count = comment_count
            item.collect_count = collect_count
            item.share_count = 0
            item.engagement_score = like_count + comment_count * 2
            item.topic_tags = self._extract_tags(f"{title}\n{snippet}")
            item.quality_score = self._build_quality_score(item)
            item.missing_fields = self._build_missing_fields(item)
            item.parse_status = self._build_parse_status(item)
            item.meta = ContentMeta(
                rank=1,
                page_no=1,
                position=1,
                collector="playwright",
                collector_version=self.COLLECTOR_VERSION,
                search_url=url,
                extracted_from="detail",
            )
            item.raw_data = {
                "detail_url": url,
            }
            item.debug_info = {
                "parse_version": self.COLLECTOR_VERSION,
            }
            return item

        except Exception as ex:
            item.parse_status = "failed"
            item.error_message = str(ex)
            item.raw_data = {"detail_url": url}
            return item

        finally:
            context.close()
            browser.close()
            playwright.stop()

    def _build_item(
        self,
        keyword: str,
        search_url: str,
        full_url: str,
        source_id: str,
        title: str,
        author_name: str,
        snippet: str,
        cover_url: str,
        like_count: int,
        comment_count: int,
        raw_text: str,
        href: str,
        rank: int,
        position: int,
    ) -> ContentItem:
        topic_tags = self._extract_tags(f"{title}\n{snippet}")
        item = ContentItem(
            platform="xiaohongshu",
            keyword=keyword,
            source_id=source_id,
            source_type="note",
            title=title[:200],
            author_name=author_name[:100],
            snippet=snippet,
            content_text="",
            content_html="",
            url=full_url,
            cover_url=cover_url,
            image_urls=[cover_url] if cover_url else [],
            publish_time="",
            like_count=like_count,
            comment_count=comment_count,
            collect_count=0,
            share_count=0,
            engagement_score=like_count + comment_count * 2,
            topic_tags=topic_tags,
            matched_keyword=keyword,
            meta=ContentMeta(
                rank=rank,
                page_no=1,
                position=position,
                collector="playwright",
                collector_version=self.COLLECTOR_VERSION,
                search_url=search_url,
                extracted_from="search_result",
            ),
            raw_data={
                "card_text": raw_text,
                "href": href,
            },
            debug_info={
                "card_text": raw_text,
                "parse_version": self.COLLECTOR_VERSION,
            },
        )
        item.quality_score = self._build_quality_score(item)
        item.missing_fields = self._build_missing_fields(item)
        item.parse_status = self._build_parse_status(item)
        return item

    def _extract_note_href(self, card) -> str:
        try:
            links = card.locator("a").all()
            for a in links:
                href = a.get_attribute("href")
                if href and "/explore/" in href:
                    return href
        except Exception:
            pass
        return ""

    def _extract_cover_url(self, card) -> str:
        try:
            img = card.locator("img").first
            if img.count() > 0:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src:
                    return src
        except Exception:
            pass
        return ""

    def _parse_card_text(self, text: str) -> tuple[str, str, int, int, str]:
        lines = [self._clean_text(line) for line in text.split("\n") if self._clean_text(line)]
        title = lines[0] if lines else ""
        author_name = ""
        if len(lines) >= 2:
            author_name = lines[-2]
        snippet_lines = lines[1:4] if len(lines) > 1 else []
        snippet = " ".join(snippet_lines).strip()[:300]

        like_source = lines[-1] if lines else text
        like_count = self._extract_first_count(like_source)
        comment_count = 0

        return title, author_name, like_count, comment_count, snippet

    def _extract_first_count(self, text: str) -> int:
        match = re.search(r"(\d+(?:\.\d+)?\s*[万wW]?)", text)
        if not match:
            return 0
        return self._to_int_count(match.group(1))

    def _normalize_count(self, text: str, pattern: str) -> int:
        match = re.search(pattern, text)
        if not match:
            return 0
        return self._to_int_count(match.group(1))

    def _to_int_count(self, value: str) -> int:
        if not value:
            return 0

        normalized = value.replace(",", "").replace(" ", "").lower()
        normalized = normalized.replace("w", "万")
        try:
            if normalized.endswith("万"):
                return int(float(normalized[:-1]) * 10000)
            return int(float(normalized))
        except Exception:
            return 0

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _extract_tags(self, text: str) -> list[str]:
        tags = re.findall(r"#([^#\s]{1,30})", text or "")
        return list(dict.fromkeys(tags))[:8]

    def _build_snippet(self, text: str) -> str:
        clean = self._clean_text(text)
        return clean[:500]

    def _build_quality_score(self, item: ContentItem) -> int:
        score = 0
        if item.title:
            score += 20
        if item.author_name:
            score += 10
        if item.url:
            score += 20
        if item.source_id:
            score += 10
        if item.like_count > 0:
            score += 10
        if item.comment_count > 0:
            score += 10
        if item.cover_url:
            score += 10
        if item.snippet:
            score += 10
        return min(score, 100)

    def _build_missing_fields(self, item: ContentItem) -> list[str]:
        missing = []
        if not item.title:
            missing.append("title")
        if not item.author_name:
            missing.append("author_name")
        if not item.publish_time:
            missing.append("publish_time")
        if not item.cover_url:
            missing.append("cover_url")
        return missing

    def _build_parse_status(self, item: ContentItem) -> str:
        if not item.title or not item.url:
            return "failed"
        if item.missing_fields:
            return "partial"
        return "ok"

    def _extract_image_urls(self, page) -> list[str]:
        urls = []
        try:
            imgs = page.locator("img").all()
            for img in imgs:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if not src:
                    continue
                if src.startswith("data:"):
                    continue
                urls.append(src)
        except Exception:
            return []
        return list(dict.fromkeys(urls))[:20]

    def _build_detail_url(self, source_id: str) -> str:
        if not source_id:
            return ""
        return f"https://www.xiaohongshu.com/explore/{source_id}"

    def _extract_source_id(self, url: str) -> str:
        if not url:
            return ""
        return url.rstrip("/").split("/")[-1]
