from typing import List
from urllib.parse import urljoin, quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.collectors.base import BaseCollector
from app.schemas.result import ContentItem
from app.utils.browser import create_browser


class XiaohongshuCollector(BaseCollector):
    BASE_URL = "https://www.xiaohongshu.com"

    def collect(self, keyword: str, max_items: int) -> List[ContentItem]:
        playwright, browser, context, page = create_browser()
        results: List[ContentItem] = []
        seen_urls = set()

        try:
            search_url = (
                f"https://www.xiaohongshu.com/search_result"
                f"?keyword={quote(keyword)}&source=web_search_result_notes&type=51"
            )
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            scroll_round = 0
            max_scroll_round = 15

            while len(results) < max_items and scroll_round < max_scroll_round:
                cards = page.locator("section").all()

                for card in cards:
                    try:
                        text = card.inner_text(timeout=2000).strip()
                        if not text:
                            continue

                        href = self._extract_note_href(card)
                        if not href:
                            continue

                        full_url = urljoin(self.BASE_URL, href)
                        if full_url in seen_urls:
                            continue

                        title, author, like_count = self._parse_card_text(text)

                        item = ContentItem(
                            platform="xiaohongshu",
                            keyword=keyword,
                            title=title[:200],
                            author=author[:100],
                            content=text[:1000],
                            url=full_url,
                            cover_url="",
                            like_count=like_count[:50],
                            comment_count="",
                            publish_time="",
                            source_id=self._extract_source_id(full_url),
                            raw_data={},
                        )

                        results.append(item)
                        seen_urls.add(full_url)

                        if len(results) >= max_items:
                            break

                    except Exception:
                        continue

                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(2500)
                scroll_round += 1

            return results

        except PlaywrightTimeoutError:
            return results

        except Exception:
            return results

        finally:
            context.close()
            browser.close()
            playwright.stop()

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

    def _parse_card_text(self, text: str):
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        title = lines[0] if len(lines) >= 1 else ""
        author = lines[-2] if len(lines) >= 2 else ""
        like_count = lines[-1] if len(lines) >= 1 else ""
        return title, author, like_count

    def _extract_source_id(self, url: str) -> str:
        if not url:
            return ""
        return url.rstrip("/").split("/")[-1]
