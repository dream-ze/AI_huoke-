"""
抖音采集器实现。

参考小红书采集器的实现模式，支持：
- 关键词搜索采集
- 单链接详情采集（支持短链 v.douyin.com）
- 反爬钩子集成
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin
from uuid import uuid4

from app.collector.adapters.base import BaseCollector
from app.collector.services.enricher import enrich_item, should_drop
from app.collector.services.normalizer import build_item
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem
from app.utils.browser import create_browser
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class DouyinCollector(BaseCollector):
    """
    抖音平台采集器。

    支持：
    - 关键词搜索采集：导航至抖音搜索页，滚动加载视频列表
    - 单链接详情采集：支持 v.douyin.com 短链自动重定向
    """

    BASE_URL = "https://www.douyin.com"
    SEARCH_URL = "https://www.douyin.com/search"

    def __init__(self) -> None:
        """初始化抖音采集器，设置平台名和目录。"""
        super().__init__()
        self.platform = "douyin"
        root_dir = Path(__file__).resolve().parents[2]
        self._artifacts_dir = root_dir / "artifacts"
        self._screenshots_dir = self._artifacts_dir / "screenshots"
        self._html_dir = self._artifacts_dir / "html"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._html_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, req: CollectRequest) -> tuple[list[ContentItem], CollectStats]:
        """
        关键词搜索采集。

        Args:
            req: 采集请求参数，包含关键词、最大数量等

        Returns:
            (items, stats): 采集到的内容列表和统计信息
        """
        task_id = f"collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        stats = CollectStats()
        items: list[ContentItem] = []
        seeds: list[dict] = []
        seen_keys: set[str] = set()

        logger.info(f"[{task_id}] 开始抖音采集，关键词: {req.keyword}")

        playwright, browser, context, page = create_browser()
        page.set_default_timeout(req.timeout_sec * 1000)

        try:
            # 构建搜索URL
            search_url = f"{self.SEARCH_URL}/{quote(req.keyword)}?type=video"
            logger.debug(f"[{task_id}] 导航至搜索页: {search_url}")

            # 导航前钩子
            self.before_navigate(page)
            page.goto(search_url, wait_until="domcontentloaded")
            # 导航后钩子
            self.after_navigate(page)
            page.wait_for_timeout(3000)

            # 滚动加载列表
            scroll_round = 0
            max_scroll_round = 10  # 抖音页面较重，限制滚动轮数

            while len(seeds) < req.max_items and scroll_round < max_scroll_round:
                # 解析当前页面的视频卡片
                # 抖音搜索结果使用 data-e2e 属性或通用 class
                card_selectors = [
                    "[data-e2e='search-video-card']",
                    "[data-e2e='search-common-video']",
                    "li[data-e2e='search-result-card']",
                    ".video-card",
                    "[class*='VideoCard']",
                ]

                for selector in card_selectors:
                    cards = page.locator(selector).all()
                    if not cards:
                        continue

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
                        logger.debug(f"[{task_id}] 发现视频: {raw.get('title', '')[:30]}...")

                        if len(seeds) >= req.max_items:
                            break

                    if seeds:
                        break  # 已找到卡片，跳出选择器循环

                if len(seeds) >= req.max_items:
                    break

                # 滚动加载更多
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(2000)
                scroll_round += 1
                logger.debug(f"[{task_id}] 滚动第 {scroll_round} 轮，已发现 {len(seeds)} 条")

            logger.info(f"[{task_id}] 列表采集完成，共发现 {len(seeds)} 条")

            # 处理每条种子数据
            for raw in seeds:
                item = build_item(raw=raw, keyword=req.keyword, task_id=task_id)
                stats.list_success += 1

                # 可选：抓取详情
                if req.need_detail:
                    item.detail_attempted = True
                    item.parse_stage = "detail"
                    stats.detail_attempted += 1

                    try:
                        detail_data = self._fetch_detail_data(page, item.url, req.need_comments)
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
                        logger.warning(f"[{task_id}] 详情采集失败: {ex}")
                        item.parse_status = "detail_failed"
                        item.detail_error = str(ex)
                        stats.detail_failed += 1

                # 数据增强
                item = enrich_item(item)

                if should_drop(item):
                    item.parse_status = "dropped"
                    stats.dropped += 1

                items.append(item)

            logger.info(
                f"[{task_id}] 采集完成: 列表 {stats.list_success}, "
                f"详情成功 {stats.detail_success}, 详情失败 {stats.detail_failed}"
            )

            return items, stats

        except Exception as e:
            logger.error(f"[{task_id}] 采集异常: {e}")
            raise
        finally:
            context.close()
            browser.close()
            playwright.stop()

    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        """
        单链接详情采集。

        支持 v.douyin.com 短链，通过 page.goto 自动跟随重定向。

        Args:
            req: 详情采集请求，包含 URL 或 source_id

        Returns:
            ContentItem: 采集到的内容详情
        """
        task_id = f"collect_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        url = req.url or self._build_detail_url(req.source_id or "")
        source_id = req.source_id or self._extract_source_id(url)

        logger.info(f"[{task_id}] 开始详情采集: {url}")

        item = build_item(
            raw={
                "source_platform": req.platform or "douyin",
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
            logger.info(f"[{task_id}] 详情采集完成: {result.parse_status}")
            return enrich_item(result)

        except Exception as ex:
            logger.error(f"[{task_id}] 详情采集异常: {ex}")
            item.parse_status = "detail_failed"
            item.detail_error = str(ex)
            return enrich_item(item)

        finally:
            context.close()
            browser.close()
            playwright.stop()

    def _parse_list_card(self, card) -> dict | None:
        """
        解析列表卡片元素。

        提取：标题、作者、播放量、点赞、评论数、视频URL

        Args:
            card: Playwright locator 元素

        Returns:
            解析后的字典，或 None（解析失败时）
        """
        # 提取视频链接
        href = self._first_attr(card, 'a[href*="/video/"]', "href")
        if not href:
            # 尝试其他选择器
            href = self._first_attr(card, "a[href]", "href")
            if not href:
                return None

        # 构建完整URL
        full_url = urljoin(self.BASE_URL, href)
        source_id = self._extract_source_id(full_url)

        # 提取标题/描述
        title = self._first_text(
            card,
            [
                "[data-e2e='video-title']",
                "[class*='title']",
                "[class*='Title']",
                "h3",
                "a[href*='/video/']",
            ],
        )

        # 提取作者名称
        author_name = self._first_text(
            card,
            [
                "[data-e2e='video-author-nickname']",
                "[class*='author']",
                "[class*='Author']",
                "[class*='name']",
            ],
        )

        # 提取封面图
        cover_url = self._first_attr(card, "img", "src")

        # 提取互动数据
        # 播放量
        views_text = self._first_text(
            card,
            [
                "[data-e2e='video-play-count']",
                "[class*='play']",
                "[class*='view']",
            ],
        )
        play_count = self._to_int_count(views_text)

        # 点赞数
        likes_text = self._first_text(
            card,
            [
                "[data-e2e='video-like-count']",
                "[class*='like']",
                "[class*='Like']",
                "[class*='digg']",
            ],
        )
        like_count = self._to_int_count(likes_text)

        # 评论数
        comments_text = self._first_text(
            card,
            [
                "[data-e2e='video-comment-count']",
                "[class*='comment']",
                "[class*='Comment']",
            ],
        )
        comment_count = self._to_int_count(comments_text)

        if not title and not author_name:
            return None

        return {
            "source_platform": "douyin",
            "source_type": "video",
            "source_id": source_id,
            "url": full_url,
            "title": self._clean_text(title),
            "snippet": self._clean_text(title)[:200] if title else "",
            "author_name": self._clean_text(author_name),
            "cover_url": self._normalize_url(cover_url),
            "play_count": play_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "parse_stage": "list",
            "parse_status": "list_only",
            "raw_data": {"stage": "list", "href": href},
        }

    def _fetch_detail_data(self, page: Page, url: str, need_comments: bool) -> dict:
        """
        抓取视频详情页数据。

        支持 v.douyin.com 短链自动重定向。

        Args:
            page: Playwright page 实例
            url: 视频URL（支持短链）
            need_comments: 是否抓取评论

        Returns:
            详情数据字典
        """
        # 导航前钩子
        self.before_navigate(page)

        # 支持短链重定向
        page.goto(url, wait_until="domcontentloaded")

        # 导航后钩子
        self.after_navigate(page)
        page.wait_for_timeout(3000)

        # 获取最终URL（处理短链重定向）
        final_url = page.url
        source_id = self._extract_source_id(final_url)

        # 提取视频描述/标题
        title = self._first_text(
            page,
            [
                "[data-e2e='video-desc']",
                "[class*='video-title']",
                "[class*='VideoTitle']",
                "[class*='desc']",
                "h1",
            ],
        )

        # 提取完整描述文本
        content_text = self._first_text(
            page,
            [
                "[data-e2e='video-desc']",
                "[class*='video-desc']",
                "[class*='Desc']",
            ],
        )

        # 提取作者信息
        author_name = self._first_text(
            page,
            [
                "[data-e2e='video-author-nickname']",
                "[class*='author'] [class*='name']",
                "[class*='nickname']",
            ],
        )

        author_url = self._first_attr(
            page,
            'a[href*="/user/"]',
            "href",
        )

        # 提取封面图
        cover_url = self._first_attr(
            page,
            [
                "video",
                "[class*='poster'] img",
                "img[class*='cover']",
            ],
            "poster",
        ) or self._first_attr(page, "video img", "src")

        # 提取互动数据
        like_count = self._extract_metric_by_label(page, "点赞")
        comment_count = self._extract_metric_by_label(page, "评论") if need_comments else None
        collect_count = self._extract_metric_by_label(page, "收藏")
        share_count = self._extract_metric_by_label(page, "分享")

        # 提取发布时间
        publish_time = self._extract_publish_time(page)

        # 提取话题标签
        tags = self._extract_tags(page)

        # 提取热门评论
        comments = []
        if need_comments:
            comments = self._extract_hot_comments(page, limit=10)

        return {
            "source_id": source_id,
            "url": final_url,
            "title": self._clean_text(title),
            "content_text": self._clean_text(content_text),
            "snippet": self._clean_text(content_text)[:200] if content_text else "",
            "author_name": self._clean_text(author_name),
            "author_home_url": self._normalize_url(author_url),
            "cover_url": self._normalize_url(cover_url),
            "publish_time": publish_time,
            "like_count": like_count,
            "comment_count": comment_count,
            "collect_count": collect_count,
            "share_count": share_count,
            "tags": tags,
            "raw_comments": comments,
            "parse_stage": "detail",
            "detail_error": "",
            "raw_data": {"stage": "detail", "final_url": final_url},
        }

    def _is_detail_success(self, item: dict) -> bool:
        """
        判断详情采集是否成功。

        Args:
            item: 内容数据字典

        Returns:
            是否成功
        """
        content_text = (item.get("content_text") or "").strip()
        title = (item.get("title") or "").strip()

        # 至少要有标题或内容
        has_content = bool(content_text) or bool(title)

        # 还需要有其他补充信息
        has_supplement = (
            item.get("publish_time") is not None
            or item.get("like_count") is not None
            or item.get("comment_count") is not None
            or item.get("author_name")
        )

        return has_content and has_supplement

    def _extract_metric_by_label(self, page: Page, label: str) -> int | None:
        """
        通过标签文本提取互动数据。

        Args:
            page: Playwright page 实例
            label: 标签文本（如"点赞"、"评论"）

        Returns:
            提取到的数值，或 None
        """
        selectors = [
            f"[aria-label*='{label}']",
            f"[title*='{label}']",
            f"button:has-text('{label}')",
            f"[class*='count']:near(:text('{label}'))",
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector)
                if locator.count() <= 0:
                    continue

                text = self._clean_text(locator.first.inner_text(timeout=500))
                if not text:
                    continue

                number = self._extract_count_from_text(text)
                if number is not None:
                    return number
            except Exception:
                continue

        # 尝试通过数字格式直接匹配
        try:
            count_locator = page.locator(f"button:has-text('{label}') [class*='count']")
            if count_locator.count() > 0:
                text = self._clean_text(count_locator.first.inner_text(timeout=500))
                return self._to_int_count(text)
        except Exception:
            pass

        return None

    def _extract_publish_time(self, page: Page) -> str | None:
        """
        提取发布时间。

        Args:
            page: Playwright page 实例

        Returns:
            ISO 格式时间字符串，或 None
        """
        selectors = [
            "time",
            "[class*='publish']",
            "[class*='time']",
            "[data-e2e='video-publish-time']",
        ]

        for selector in selectors:
            text = self._first_text(page, [selector])
            parsed = self._parse_datetime_text(text)
            if parsed:
                return parsed

        # 尝试从页面源码中提取
        try:
            html = page.content()
            match = re.search(
                r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
                html,
            )
            if match:
                year, month, day, hour, minute, second = match.groups()
                try:
                    return (
                        datetime(
                            int(year),
                            int(month),
                            int(day),
                            int(hour),
                            int(minute),
                            int(second or 0),
                        )
                        .astimezone()
                        .isoformat()
                    )
                except ValueError:
                    pass
        except Exception:
            pass

        return None

    def _extract_tags(self, page: Page) -> list[str]:
        """
        提取话题标签。

        Args:
            page: Playwright page 实例

        Returns:
            标签列表
        """
        tags: list[str] = []

        # 抖音话题标签通常是 a 标签，href 包含 /hashtag/
        try:
            tag_locator = page.locator('a[href*="/hashtag/"], a[href*="/topic/"]')
            count = tag_locator.count()

            for idx in range(min(count, 10)):
                try:
                    tag_text = tag_locator.nth(idx).inner_text(timeout=300)
                    cleaned = self._clean_text(tag_text)
                    if cleaned and cleaned.startswith("#"):
                        tags.append(cleaned)
                    elif cleaned:
                        tags.append(f"#{cleaned}")
                except Exception:
                    continue

        except Exception:
            pass

        # 去重
        return list(dict.fromkeys(tags))

    def _extract_hot_comments(self, page: Page, limit: int = 10) -> list[dict]:
        """
        提取热门评论。

        Args:
            page: Playwright page 实例
            limit: 最大评论数

        Returns:
            评论列表
        """
        comments: list[dict] = []

        try:
            # 抖音评论选择器
            comment_selectors = [
                "[data-e2e='comment-item']",
                "[class*='comment-item']",
                "[class*='CommentItem']",
            ]

            for selector in comment_selectors:
                locator = page.locator(selector)
                count = locator.count()

                if count <= 0:
                    continue

                for idx in range(min(count, limit)):
                    try:
                        item = locator.nth(idx)

                        # 提取评论文本
                        text = self._first_text(
                            item,
                            [
                                "[class*='comment-text']",
                                "[class*='content']",
                                "p",
                            ],
                        )

                        # 提取评论作者
                        author = self._first_text(item, ["[class*='author']", "[class*='name']"])

                        # 提取点赞数
                        likes_text = self._first_text(item, ["[class*='like']", "[class*='count']"])
                        likes = self._to_int_count(likes_text)

                        if text:
                            comments.append(
                                {
                                    "author": self._clean_text(author),
                                    "text": self._clean_text(text),
                                    "likes": likes,
                                }
                            )

                    except Exception:
                        continue

                break  # 已找到评论，跳出选择器循环

        except Exception as e:
            logger.warning(f"提取评论失败: {e}")

        return comments

    def _extract_source_id(self, url: str) -> str:
        """
        从 URL 中提取视频 ID。

        Args:
            url: 视频URL

        Returns:
            视频ID
        """
        if not url:
            return ""

        # 匹配 /video/{id} 模式
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)

        # 匹配 modal_id 参数
        match = re.search(r"modal_id=(\d+)", url)
        if match:
            return match.group(1)

        # 从路径末尾提取
        return url.rstrip("/").split("/")[-1]

    def _build_detail_url(self, source_id: str) -> str:
        """
        根据 source_id 构建详情页 URL。

        Args:
            source_id: 视频 ID

        Returns:
            详情页 URL
        """
        if not source_id:
            return ""
        return f"{self.BASE_URL}/video/{source_id}"

    def _first_text(self, scope, selectors: list[str]) -> str:
        """
        从多个选择器中获取第一个匹配元素的文本。

        Args:
            scope: Playwright locator 或 page
            selectors: 选择器列表

        Returns:
            元素文本，或空字符串
        """
        for selector in selectors:
            try:
                locator = scope.locator(selector)
                if locator.count() <= 0:
                    continue
                value = (locator.first.inner_text(timeout=500) or "").strip()
                if value:
                    return value
            except Exception:
                continue
        return ""

    def _first_attr(self, scope, selectors: str | list[str], attr: str) -> str:
        """
        从选择器获取元素的属性值。

        Args:
            scope: Playwright locator 或 page
            selectors: 选择器或选择器列表
            attr: 属性名

        Returns:
            属性值，或空字符串
        """
        if isinstance(selectors, str):
            selectors = [selectors]

        for selector in selectors:
            try:
                locator = scope.locator(selector)
                if locator.count() <= 0:
                    continue
                value = locator.first.get_attribute(attr)
                if value:
                    return value.strip()
            except Exception:
                continue
        return ""

    def _to_int_count(self, text: str | None) -> int:
        """
        将文本数字转换为整数。

        支持格式：1.2万、1.2w、12.5亿等

        Args:
            text: 数字文本

        Returns:
            整数值
        """
        if not text:
            return 0

        normalized = text.replace(",", "").replace(" ", "").lower().replace("w", "万").replace("k", "千")

        try:
            if "亿" in normalized:
                num_str = normalized.replace("亿", "")
                return int(float(num_str) * 100000000)
            if "万" in normalized:
                num_str = normalized.replace("万", "")
                return int(float(num_str) * 10000)
            if "千" in normalized:
                num_str = normalized.replace("千", "")
                return int(float(num_str) * 1000)

            return int(float(normalized))
        except Exception:
            return 0

    def _extract_count_from_text(self, text: str) -> int | None:
        """
        从文本中提取数字。

        Args:
            text: 包含数字的文本

        Returns:
            提取到的数字，或 None
        """
        match = re.search(r"(\d+(?:\.\d+)?(?:万|w|W|亿|千|k)?)", text)
        if not match:
            return None
        return self._to_int_count(match.group(1))

    def _clean_text(self, text: str | None) -> str:
        """
        清理文本中的多余空白。

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        return re.sub(r"\s+", " ", text or "").strip()

    def _normalize_url(self, url: str | None) -> str | None:
        """
        标准化 URL。

        Args:
            url: 原始 URL

        Returns:
            标准化后的 URL，或 None
        """
        if not url:
            return None

        text = url.strip()
        if not text or text.startswith("data:"):
            return None

        match = re.match(r"^(https?://[^?#]+)", text)
        if not match:
            return None

        return match.group(1)

    def _parse_datetime_text(self, text: str) -> str | None:
        """
        解析日期时间文本。

        Args:
            text: 日期时间文本

        Returns:
            ISO 格式时间字符串，或 None
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        # 匹配完整时间格式
        exact_match = re.search(
            r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+|T)(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
            cleaned,
        )
        if exact_match:
            year, month, day, hour, minute, second = exact_match.groups()
            try:
                return (
                    datetime(
                        int(year),
                        int(month),
                        int(day),
                        int(hour),
                        int(minute),
                        int(second or 0),
                    )
                    .astimezone()
                    .isoformat()
                )
            except ValueError:
                return None

        # 匹配仅日期格式
        date_only_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
        if not date_only_match:
            return None

        year, month, day = date_only_match.groups()
        try:
            return datetime(int(year), int(month), int(day), 0, 0, 0).astimezone().isoformat()
        except ValueError:
            return None
