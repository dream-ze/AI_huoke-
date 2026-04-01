"""
知乎平台采集器实现

支持三种内容类型：
- 文章页 (zhuanlan.zhihu.com/p/xxx)
- 回答页 (zhihu.com/question/xxx/answer/yyy)
- 问题页 (zhihu.com/question/xxx)
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from app.collector.adapters.base import BaseCollector
from app.collector.services.enricher import enrich_item, should_drop
from app.collector.services.normalizer import build_item
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem
from app.utils.browser import create_browser
from playwright.sync_api import Locator, Page

logger = logging.getLogger(__name__)


class ZhihuCollector(BaseCollector):
    """知乎平台内容采集器"""

    BASE_URL = "https://www.zhihu.com"
    ZHUANLAN_URL = "https://zhuanlan.zhihu.com"
    SEARCH_URL = "https://www.zhihu.com/search"

    # 内容类型常量
    CONTENT_TYPE_ARTICLE = "article"
    CONTENT_TYPE_ANSWER = "answer"
    CONTENT_TYPE_QUESTION = "question"

    def __init__(self) -> None:
        """初始化知乎采集器"""
        super().__init__()
        self.platform = "zhihu"
        root_dir = Path(__file__).resolve().parents[2]
        self._artifacts_dir = root_dir / "artifacts"
        self._screenshots_dir = self._artifacts_dir / "screenshots"
        self._html_dir = self._artifacts_dir / "html"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._html_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ZhihuCollector initialized")

    def collect(self, req: CollectRequest) -> tuple[list[ContentItem], CollectStats]:
        """
        关键词搜索采集

        Args:
            req: 采集请求参数

        Returns:
            (items, stats): 采集到的内容列表和统计信息
        """
        task_id = f"collect_zhihu_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        stats = CollectStats()
        items: list[ContentItem] = []
        seeds: list[dict] = []
        seen_keys: set[str] = set()

        logger.info(f"Starting zhihu collection, task_id={task_id}, keyword={req.keyword}")

        playwright, browser, context, page = create_browser()
        page.set_default_timeout(req.timeout_sec * 1000)

        try:
            # 导航至知乎搜索页
            search_url = f"{self.SEARCH_URL}?type=content&q={req.keyword}"
            logger.debug(f"Navigating to search URL: {search_url}")

            self.before_navigate(page)
            page.goto(search_url, wait_until="domcontentloaded")
            self.after_navigate(page)
            page.wait_for_timeout(3000)

            # 智能滚动加载列表（最多10轮）
            scroll_round = 0
            max_scroll_round = 10

            while len(seeds) < req.max_items and scroll_round < max_scroll_round:
                # 解析当前页面的搜索结果卡片
                cards = self._get_search_result_cards(page)
                logger.debug(f"Scroll round {scroll_round}: found {len(cards)} cards")

                for card in cards:
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

                # 滚动加载更多
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2000)
                scroll_round += 1

            logger.info(f"Collected {len(seeds)} seeds from search results")

            # 构建内容项并可选获取详情
            for raw in seeds:
                item = build_item(raw=raw, keyword=req.keyword, task_id=task_id)
                stats.list_success += 1

                if req.need_detail:
                    item.detail_attempted = True
                    item.parse_stage = "detail"
                    stats.detail_attempted += 1

                    try:
                        detail_data = self._fetch_detail_data(page, item.url, item.source_type, req.need_comments)
                        merged = item.model_dump()
                        merged.update(detail_data)
                        merged["parse_stage"] = "detail"
                        merged["parse_status"] = (
                            "detail_success" if self._is_detail_success(merged) else "detail_failed"
                        )
                        item = ContentItem(**merged)

                        if item.parse_status == "detail_success":
                            stats.detail_success += 1
                        else:
                            stats.detail_failed += 1
                    except Exception as ex:
                        logger.warning(f"Failed to fetch detail for {item.url}: {ex}")
                        item.parse_status = "detail_failed"
                        item.detail_error = str(ex)
                        stats.detail_failed += 1

                item = enrich_item(item)

                if should_drop(item):
                    item.parse_status = "dropped"
                    stats.dropped += 1

                items.append(item)

            logger.info(f"Collection completed, task_id={task_id}, " f"total={len(items)}, stats={stats.model_dump()}")
            return items, stats

        finally:
            context.close()
            browser.close()
            playwright.stop()

    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        """
        单链接详情采集

        Args:
            req: 详情采集请求

        Returns:
            ContentItem: 包含完整详情的内容项
        """
        task_id = f"fetch_detail_zhihu_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        url = req.url or ""
        source_id = req.source_id or self._extract_source_id(url)
        content_type = self._detect_content_type(url)

        logger.info(f"Fetching detail, task_id={task_id}, url={url}, type={content_type}")

        item = build_item(
            raw={
                "source_platform": "zhihu",
                "source_type": content_type,
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
            detail_data = self._fetch_detail_data(page, url, content_type, need_comments=True)
            merged = item.model_dump()
            merged.update(detail_data)
            merged["parse_stage"] = "detail"
            merged["parse_status"] = "detail_success" if self._is_detail_success(merged) else "detail_failed"
            result = ContentItem(**merged)
            return enrich_item(result)
        except Exception as ex:
            logger.error(f"Failed to fetch detail for {url}: {ex}")
            item.parse_status = "detail_failed"
            item.detail_error = str(ex)
            return enrich_item(item)
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def _get_search_result_cards(self, page: Page) -> list[Locator]:
        """获取搜索结果卡片列表"""
        selectors = [
            ".SearchResult-Card",
            ".List-item",
            ".Card.SearchResult-Card",
            "[class*=SearchResult]",
        ]

        all_cards: list[Locator] = []
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            if count > 0:
                for idx in range(count):
                    all_cards.append(locator.nth(idx))

        # 去重
        seen_elements: set[int] = set()
        unique_cards: list[Locator] = []
        for card in all_cards:
            try:
                element_handle = card.element_handle()
                element_id = id(element_handle)
                if element_id not in seen_elements:
                    seen_elements.add(element_id)
                    unique_cards.append(card)
            except Exception:
                continue

        return unique_cards

    def _parse_list_card(self, card: Locator) -> dict | None:
        """
        解析列表卡片

        Args:
            card: 搜索结果卡片元素

        Returns:
            解析后的数据字典，解析失败返回 None
        """
        try:
            # 提取链接
            href = self._first_attr(card, 'a[href*="question"], a[href*="zhuanlan"]', "href")
            if not href:
                return None

            # 构建完整 URL
            if href.startswith("//"):
                full_url = "https:" + href
            elif href.startswith("/"):
                full_url = urljoin(self.BASE_URL, href)
            else:
                full_url = href

            # 检测内容类型
            content_type = self._detect_content_type(full_url)
            source_id = self._extract_source_id(full_url)

            # 提取标题
            title = self._first_text(
                card,
                [
                    ".ContentItem-title a",
                    ".ContentItem-title",
                    "h2.ContentItem-title",
                    "[class*=title]",
                    "a[data-za-detail-view-element_name*=Title]",
                ],
            )

            # 提取摘要
            snippet = self._first_text(
                card,
                [
                    ".RichContent-inner",
                    ".RichText",
                    "[class*=excerpt]",
                    "[class*=summary]",
                ],
            )

            # 提取作者
            author_name = self._first_text(
                card,
                [
                    ".AuthorInfo-name",
                    ".UserLink-link",
                    "[class*=author]",
                ],
            )

            author_url = self._first_attr(card, ".AuthorInfo-name a, .UserLink-link", "href")
            if author_url and not author_url.startswith("http"):
                author_url = urljoin(self.BASE_URL, author_url)

            # 提取赞同数
            vote_text = self._first_text(
                card,
                [
                    "[class*=VoteCount]",
                    ".VoteButton--up",
                    "button[aria-label*=赞同]",
                ],
            )
            like_count = self._parse_count_text(vote_text)

            # 提取评论数
            comment_text = self._first_text(
                card,
                [
                    "[class*=CommentCount]",
                    "button[aria-label*=评论]",
                ],
            )
            comment_count = self._parse_count_text(comment_text)

            # 提取回答数（仅问题类型）
            answer_text = self._first_text(
                card,
                [
                    "[class*=answerCount]",
                    "span:has-text('回答')",
                ],
            )
            answer_count = self._parse_count_text(answer_text)

            if not title and not snippet:
                return None

            return {
                "source_platform": "zhihu",
                "source_type": content_type,
                "source_id": source_id,
                "url": full_url,
                "title": self._clean_text(title),
                "snippet": self._clean_text(snippet),
                "author_name": self._clean_text(author_name),
                "author_home_url": author_url,
                "like_count": like_count,
                "comment_count": comment_count,
                "collect_count": answer_count if content_type == self.CONTENT_TYPE_QUESTION else None,
                "parse_stage": "list",
                "parse_status": "list_only",
                "raw_data": {"stage": "list", "href": href},
            }
        except Exception as ex:
            logger.debug(f"Failed to parse list card: {ex}")
            return None

    def _fetch_detail_data(self, page: Page, url: str, content_type: str, need_comments: bool) -> dict:
        """
        获取详情数据

        Args:
            page: Playwright 页面对象
            url: 详情页 URL
            content_type: 内容类型 (article/answer/question)
            need_comments: 是否采集评论

        Returns:
            详情数据字典
        """
        self.before_navigate(page)
        page.goto(url, wait_until="domcontentloaded")
        self.after_navigate(page)
        page.wait_for_timeout(2500)

        # 点击"展开阅读全文"按钮
        self._click_expand_button(page)

        if content_type == self.CONTENT_TYPE_ARTICLE:
            return self._parse_article_detail(page, need_comments)
        elif content_type == self.CONTENT_TYPE_ANSWER:
            return self._parse_answer_detail(page, need_comments)
        elif content_type == self.CONTENT_TYPE_QUESTION:
            return self._parse_question_detail(page, need_comments)
        else:
            return self._parse_generic_detail(page, need_comments)

    def _click_expand_button(self, page: Page) -> None:
        """点击"展开阅读全文"按钮"""
        selectors = [
            "button:has-text('展开阅读全文')",
            ".ContentItem-expandButton",
            "[class*=ExpandButton]",
            ".RichContent-inner button",
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                    logger.debug("Clicked expand button")
                    break
            except Exception:
                continue

    def _parse_article_detail(self, page: Page, need_comments: bool) -> dict:
        """
        解析文章详情页

        Args:
            page: Playwright 页面对象
            need_comments: 是否采集评论

        Returns:
            文章详情数据
        """
        # 提取标题
        title = self._first_text(
            page,
            [
                "h1.Post-Title",
                ".Post-Title",
                "h1[class*=Title]",
            ],
        )

        # 提取正文
        content_text = self._first_text(
            page,
            [
                ".Post-RichText",
                ".RichText",
                "article",
                ".RichContent-inner",
            ],
        )

        # 提取作者
        author_name = self._first_text(
            page,
            [
                ".AuthorInfo-name",
                "[class*=author-name]",
            ],
        )

        author_url = self._first_attr(page, ".AuthorInfo a, [class*=author] a", "href")
        if author_url and not author_url.startswith("http"):
            author_url = urljoin(self.BASE_URL, author_url)

        # 提取发布时间
        publish_time = self._extract_publish_time(page)

        # 提取图片
        image_urls = self._extract_content_image_urls(page)

        # 提取标签
        tags = self._extract_tags(page)

        # 提取指标数据
        like_count = self._extract_metric(page, "赞同", "喜欢")
        comment_count = self._extract_metric(page, "评论") if need_comments else None
        collect_count = self._extract_metric(page, "收藏")

        return {
            "title": self._clean_text(title),
            "content_text": self._clean_text(content_text),
            "snippet": self._clean_text(content_text)[:200] if content_text else "",
            "author_name": self._clean_text(author_name),
            "author_home_url": author_url,
            "publish_time": publish_time,
            "image_urls": image_urls,
            "image_count": len(image_urls),
            "tags": tags,
            "like_count": like_count,
            "comment_count": comment_count,
            "collect_count": collect_count,
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {"stage": "detail", "content_type": "article"},
        }

    def _parse_answer_detail(self, page: Page, need_comments: bool) -> dict:
        """
        解析回答详情页

        Args:
            page: Playwright 页面对象
            need_comments: 是否采集评论

        Returns:
            回答详情数据
        """
        # 提取问题标题
        question_title = self._first_text(
            page,
            [
                "h1.QuestionHeader-title",
                ".QuestionHeader-title",
                "h1[class*=QuestionTitle]",
            ],
        )

        # 提取回答正文
        answer_text = self._first_text(
            page,
            [
                ".RichContent-inner",
                ".RichText",
                "[itemprop*=text]",
            ],
        )

        # 提取作者
        author_name = self._first_text(
            page,
            [
                ".AuthorInfo-name",
                "[class*=author-name]",
            ],
        )

        author_url = self._first_attr(page, ".AuthorInfo a, [class*=author] a", "href")
        if author_url and not author_url.startswith("http"):
            author_url = urljoin(self.BASE_URL, author_url)

        # 提取发布时间
        publish_time = self._extract_publish_time(page)

        # 提取图片
        image_urls = self._extract_content_image_urls(page)

        # 提取指标数据
        like_count = self._extract_metric(page, "赞同", "喜欢")
        comment_count = self._extract_metric(page, "评论") if need_comments else None
        collect_count = self._extract_metric(page, "收藏")

        # 提取热门评论
        comments: list[dict] = []
        if need_comments:
            comments = self._extract_hot_comments(page)

        return {
            "title": self._clean_text(question_title),
            "content_text": self._clean_text(answer_text),
            "snippet": self._clean_text(answer_text)[:200] if answer_text else "",
            "author_name": self._clean_text(author_name),
            "author_home_url": author_url,
            "publish_time": publish_time,
            "image_urls": image_urls,
            "image_count": len(image_urls),
            "tags": [],
            "like_count": like_count,
            "comment_count": comment_count,
            "collect_count": collect_count,
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {
                "stage": "detail",
                "content_type": "answer",
                "comments": comments,
            },
        }

    def _parse_question_detail(self, page: Page, need_comments: bool) -> dict:
        """
        解析问题详情页

        Args:
            page: Playwright 页面对象
            need_comments: 是否采集评论

        Returns:
            问题详情数据（包含 Top 回答列表）
        """
        # 提取问题标题
        title = self._first_text(
            page,
            [
                "h1.QuestionHeader-title",
                ".QuestionHeader-title",
                "h1[class*=QuestionTitle]",
            ],
        )

        # 提取问题描述
        question_detail = self._first_text(
            page,
            [
                ".QuestionRichText",
                ".QuestionHeader-detail",
                "[class*=QuestionDetail]",
            ],
        )

        # 提取回答数
        answer_count_text = self._first_text(
            page,
            [
                ".List-headerText",
                "[class*=answerCount]",
            ],
        )
        answer_count = self._parse_count_text(answer_count_text)

        # 提取关注数
        follow_count = self._extract_metric(page, "关注")

        # 提取 Top 回答列表
        top_answers: list[dict] = []
        answer_locators = page.locator(".List-item, [class*=AnswerItem]")
        answer_count_on_page = min(answer_locators.count(), 5)  # 最多取5个

        for idx in range(answer_count_on_page):
            try:
                answer_el = answer_locators.nth(idx)
                answer_content = self._first_text(answer_el, [".RichContent-inner", ".RichText"])
                answer_author = self._first_text(answer_el, [".AuthorInfo-name"])
                answer_likes = self._extract_metric_from_element(answer_el, "赞同")

                if answer_content:
                    top_answers.append(
                        {
                            "author": self._clean_text(answer_author),
                            "content": self._clean_text(answer_content)[:500],
                            "likes": answer_likes or 0,
                        }
                    )
            except Exception:
                continue

        # 提取标签
        tags = self._extract_tags(page)

        return {
            "title": self._clean_text(title),
            "content_text": self._clean_text(question_detail),
            "snippet": self._clean_text(question_detail)[:200] if question_detail else "",
            "like_count": follow_count,
            "collect_count": answer_count,
            "tags": tags,
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {
                "stage": "detail",
                "content_type": "question",
                "top_answers": top_answers,
            },
        }

    def _parse_generic_detail(self, page: Page, need_comments: bool) -> dict:
        """
        通用详情解析（用于未知类型页面）

        Args:
            page: Playwright 页面对象
            need_comments: 是否采集评论

        Returns:
            详情数据字典
        """
        title = self._first_text(page, ["h1", ".title", "[class*=title]"])
        content_text = self._first_text(
            page,
            [
                ".RichContent-inner",
                "article",
                ".content",
                "[class*=content]",
            ],
        )
        author_name = self._first_text(page, [".AuthorInfo-name", "[class*=author]"])
        publish_time = self._extract_publish_time(page)
        image_urls = self._extract_content_image_urls(page)

        return {
            "title": self._clean_text(title),
            "content_text": self._clean_text(content_text),
            "snippet": self._clean_text(content_text)[:200] if content_text else "",
            "author_name": self._clean_text(author_name),
            "publish_time": publish_time,
            "image_urls": image_urls,
            "image_count": len(image_urls),
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {"stage": "detail", "content_type": "unknown"},
        }

    def _extract_publish_time(self, page: Page) -> str | None:
        """提取发布时间"""
        selectors = [
            "time",
            "[class*=time]",
            "[class*=date]",
            "[class*=Time]",
            "[itemprop*=date]",
        ]

        for selector in selectors:
            text = self._first_text(page, [selector])
            if text:
                parsed = self._parse_datetime_text(text)
                if parsed:
                    return parsed

        # 尝试从 HTML 中提取
        html = page.content()
        match = re.search(
            r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
            html,
        )
        if match:
            year, month, day, hour, minute, second = match.groups()
            try:
                dt = datetime(
                    int(year),
                    int(month),
                    int(day),
                    int(hour),
                    int(minute),
                    int(second or 0),
                ).astimezone()
                return dt.isoformat()
            except ValueError:
                pass

        return None

    def _extract_content_image_urls(self, page: Page) -> list[str]:
        """提取内容图片 URL"""
        urls: list[str] = []
        selectors = [
            ".RichContent-inner img",
            ".RichText img",
            "article img",
            "[class*=content] img",
            "figure img",
        ]

        seen: set[str] = set()
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            for idx in range(count):
                try:
                    img = locator.nth(idx)
                    src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                    src = img.get_attribute("data-actualsrc") or src

                    normalized = self._normalize_url(src)
                    if normalized and normalized not in seen:
                        if not self._is_noise_image(normalized):
                            seen.add(normalized)
                            urls.append(normalized)
                except Exception:
                    continue

        return urls[:12]  # 最多返回12张图片

    def _extract_tags(self, page: Page) -> list[str]:
        """提取话题标签"""
        tags: list[str] = []

        selectors = [
            ".TagContent",
            "[class*=TopicLink]",
            "[class*=tag]",
            "a.TopicLink",
        ]

        seen: set[str] = set()
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            for idx in range(count):
                try:
                    tag_el = locator.nth(idx)
                    tag_text = tag_el.inner_text(timeout=500).strip()
                    if tag_text and tag_text not in seen:
                        seen.add(tag_text)
                        tags.append(tag_text)
                except Exception:
                    continue

        return tags[:10]  # 最多返回10个标签

    def _extract_hot_comments(self, page: Page) -> list[dict]:
        """提取热门评论"""
        comments: list[dict] = []

        try:
            # 点击展开评论
            comment_btn = page.locator("button:has-text('评论'), [class*=CommentButton]")
            if comment_btn.count() > 0:
                comment_btn.first.click(timeout=2000)
                page.wait_for_timeout(1500)

            # 提取评论项
            comment_items = page.locator("[class*=CommentItem], .CommentItem")
            count = min(comment_items.count(), 10)  # 最多取10条

            for idx in range(count):
                try:
                    item = comment_items.nth(idx)
                    author = self._first_text(item, ["[class*=author]", "[class*=name]"])
                    content = self._first_text(item, ["[class*=content]", ".RichText"])
                    likes = self._extract_metric_from_element(item, "赞")

                    if content:
                        comments.append(
                            {
                                "author": self._clean_text(author),
                                "content": self._clean_text(content)[:200],
                                "likes": likes or 0,
                            }
                        )
                except Exception:
                    continue
        except Exception as ex:
            logger.debug(f"Failed to extract comments: {ex}")

        return comments

    def _extract_metric(self, page: Page, *labels: str) -> int | None:
        """提取指标数据"""
        for label in labels:
            selectors = [
                f"button[aria-label*='{label}']",
                f"[aria-label*='{label}']",
                f"button:has-text('{label}')",
                f"[class*=VoteCount]",
            ]

            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        text = locator.first.inner_text(timeout=500)
                        count = self._parse_count_text(text)
                        if count is not None:
                            return count
                except Exception:
                    continue

        return None

    def _extract_metric_from_element(self, element: Locator, label: str) -> int | None:
        """从元素中提取指标数据"""
        selectors = [
            f"button[aria-label*='{label}']",
            f"[aria-label*='{label}']",
            "[class*=VoteCount]",
            "[class*=count]",
        ]

        for selector in selectors:
            try:
                locator = element.locator(selector)
                if locator.count() > 0:
                    text = locator.first.inner_text(timeout=500)
                    return self._parse_count_text(text)
            except Exception:
                continue

        return None

    def _detect_content_type(self, url: str) -> str:
        """
        检测内容类型

        Args:
            url: 页面 URL

        Returns:
            内容类型: article/answer/question
        """
        if not url:
            return self.CONTENT_TYPE_ANSWER  # 默认类型

        url_lower = url.lower()

        # 文章页: zhuanlan.zhihu.com/p/xxx
        if "zhuanlan.zhihu.com" in url_lower or "/p/" in url_lower:
            return self.CONTENT_TYPE_ARTICLE

        # 回答页: zhihu.com/question/xxx/answer/yyy
        if "/answer/" in url_lower:
            return self.CONTENT_TYPE_ANSWER

        # 问题页: zhihu.com/question/xxx
        if "zhihu.com/question" in url_lower:
            return self.CONTENT_TYPE_QUESTION

        return self.CONTENT_TYPE_ANSWER  # 默认类型

    def _extract_source_id(self, url: str) -> str:
        """
        从 URL 提取内容 ID

        Args:
            url: 页面 URL

        Returns:
            内容 ID
        """
        if not url:
            return ""

        # 提取文章 ID: /p/123456
        match = re.search(r"/p/(\d+)", url)
        if match:
            return f"article_{match.group(1)}"

        # 提取回答 ID: /question/123/answer/456
        match = re.search(r"/question/(\d+)/answer/(\d+)", url)
        if match:
            return f"answer_{match.group(2)}"

        # 提取问题 ID: /question/123
        match = re.search(r"/question/(\d+)", url)
        if match:
            return f"question_{match.group(1)}"

        return ""

    def _is_detail_success(self, item: dict) -> bool:
        """判断详情采集是否成功"""
        content_text = (item.get("content_text") or "").strip()
        return bool(content_text) and (
            item.get("publish_time") is not None
            or (item.get("image_count") or 0) > 0
            or item.get("comment_count") is not None
            or item.get("like_count") is not None
        )

    def _first_text(self, scope: Page | Locator, selectors: list[str]) -> str:
        """获取第一个匹配元素的文本"""
        for selector in selectors:
            try:
                locator = scope.locator(selector)
                if locator.count() > 0:
                    value = (locator.first.inner_text(timeout=500) or "").strip()
                    if value:
                        return value
            except Exception:
                continue
        return ""

    def _first_attr(self, scope: Page | Locator, selector: str, attr: str) -> str:
        """获取第一个匹配元素的属性值"""
        try:
            locator = scope.locator(selector)
            if locator.count() > 0:
                value = locator.first.get_attribute(attr, timeout=500)
                return (value or "").strip()
        except Exception:
            pass
        return ""

    def _parse_count_text(self, text: str | None) -> int | None:
        """解析数字文本"""
        if not text:
            return None

        # 提取数字部分
        match = re.search(r"(\d+(?:\.\d+)?)([万wWkK]?)", text)
        if not match:
            return None

        number_str = match.group(1)
        unit = match.group(2).lower()

        try:
            number = float(number_str)
            if unit in ("万", "w"):
                return int(number * 10000)
            elif unit == "k":
                return int(number * 1000)
            return int(number)
        except ValueError:
            return None

    def _parse_datetime_text(self, text: str) -> str | None:
        """解析日期时间文本"""
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        # 尝试匹配完整日期时间
        exact_match = re.search(
            r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
            cleaned,
        )
        if exact_match:
            year, month, day, hour, minute, second = exact_match.groups()
            try:
                dt = datetime(
                    int(year),
                    int(month),
                    int(day),
                    int(hour),
                    int(minute),
                    int(second or 0),
                ).astimezone()
                return dt.isoformat()
            except ValueError:
                pass

        # 尝试匹配日期
        date_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
        if date_match:
            year, month, day = date_match.groups()
            try:
                dt = datetime(int(year), int(month), int(day), 0, 0, 0).astimezone()
                return dt.isoformat()
            except ValueError:
                pass

        # 处理相对时间（如 "3 天前"）
        relative_match = re.search(r"(\d+)\s*(天|小时|分钟)前", cleaned)
        if relative_match:
            from datetime import timedelta

            value = int(relative_match.group(1))
            unit = relative_match.group(2)

            now = datetime.now().astimezone()
            if unit == "天":
                dt = now - timedelta(days=value)
            elif unit == "小时":
                dt = now - timedelta(hours=value)
            else:
                dt = now - timedelta(minutes=value)

            return dt.isoformat()

        return None

    def _clean_text(self, text: str | None) -> str:
        """清理文本"""
        return re.sub(r"\s+", " ", text or "").strip()

    def _normalize_url(self, url: str | None) -> str | None:
        """规范化 URL"""
        if not url:
            return None

        text = url.strip()
        if not text or text.startswith("data:"):
            return None

        # 处理知乎图片 URL
        if text.startswith("//"):
            text = "https:" + text

        match = re.match(r"^(https?://[^?#]+)", text)
        if not match:
            return None

        return match.group(1)

    def _is_noise_image(self, url: str) -> bool:
        """判断是否为噪音图片"""
        lowered = url.lower()
        noise_keywords = [
            "avatar",
            "icon",
            "logo",
            "emoji",
            "badge",
            "profile",
            "default",
            "placeholder",
            "loading",
            "ad_",
        ]
        return any(keyword in lowered for keyword in noise_keywords)
