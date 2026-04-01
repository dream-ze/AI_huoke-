import asyncio
import logging
import time
from typing import Any, Callable, Optional
from uuid import uuid4

import httpx
from app.collector.services.collect_service import CollectService
from app.collector.services.factory import CollectorFactory
from app.core.config import settings
from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest

logger = logging.getLogger(__name__)


class BrowserCollectorClient:
    """Client for browser_collector internal service.

    默认使用内部直接调用模式（不再依赖 HTTP 外部服务）。
    如果设置了 BROWSER_COLLECTOR_BASE_URL 且不是 127.0.0.1，则回退到 HTTP 调用。

    特性：
    - 指数退避重试机制（默认3次，间隔2s/4s/8s）
    - 超时降级策略（缩减采集范围后重试）
    - 断路器模式（连续失败N次后暂停）
    """

    # 指数退避重试配置
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE_SECONDS = 2

    # 断路器配置
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
    DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60  # 冷却时间60秒
    _consecutive_failures = 0
    _circuit_open = False
    _last_failure_ts: float | None = None

    def __init__(self, *, use_http: bool = False) -> None:
        self.base_url = settings.BROWSER_COLLECTOR_BASE_URL.rstrip("/")
        self.timeout_seconds = settings.BROWSER_COLLECTOR_TIMEOUT_SECONDS
        # 默认使用内部调用，除非显式指定 use_http 或 URL 不是本地地址
        self._use_http = use_http or not self._is_local_url()

    def _is_local_url(self) -> bool:
        """检查是否是本地地址（127.0.0.1 或 localhost）"""
        return "127.0.0.1" in self.base_url or "localhost" in self.base_url

    def _check_circuit_breaker(self) -> bool:
        """检查断路器状态，返回是否允许继续执行"""
        if BrowserCollectorClient._circuit_open:
            # 冷却时间过后允许试探性请求（半开状态）
            if (
                BrowserCollectorClient._last_failure_ts is not None
                and time.time() - BrowserCollectorClient._last_failure_ts
                >= self.DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS
            ):
                logger.info("Circuit breaker entering half-open state, allowing probe request")
                return True
            logger.error("Circuit breaker is OPEN - too many consecutive failures")
            return False
        return True

    def _record_failure(self) -> None:
        """记录一次失败，更新断路器状态"""
        BrowserCollectorClient._consecutive_failures += 1
        BrowserCollectorClient._last_failure_ts = time.time()
        if BrowserCollectorClient._consecutive_failures >= self.DEFAULT_CIRCUIT_BREAKER_THRESHOLD:
            BrowserCollectorClient._circuit_open = True
            logger.error(
                "Circuit breaker OPENED after %d consecutive failures", BrowserCollectorClient._consecutive_failures
            )

    def _record_success(self) -> None:
        """记录一次成功，重置失败计数"""
        if BrowserCollectorClient._consecutive_failures > 0:
            BrowserCollectorClient._consecutive_failures = 0
            logger.info("Circuit breaker failure count reset after success")
        if BrowserCollectorClient._circuit_open:
            BrowserCollectorClient._circuit_open = False
            logger.info("Circuit breaker CLOSED - resuming normal operations")

    def _exponential_backoff_retry(
        self,
        operation: Callable[[], dict[str, Any]],
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: int = DEFAULT_BACKOFF_BASE_SECONDS,
        operation_name: str = "operation",
    ) -> dict[str, Any]:
        """
        执行带指数退避重试的操作。

        Args:
            operation: 要执行的操作函数
            max_retries: 最大重试次数
            backoff_base: 退避基数（秒）
            operation_name: 操作名称（用于日志）

        Returns:
            操作结果

        Raises:
            Exception: 所有重试都失败时抛出最后一次异常
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                result = operation()
                self._record_success()
                return result
            except Exception as e:
                last_exception = e
                self._record_failure()

                if attempt < max_retries:
                    sleep_seconds = backoff_base * (2**attempt)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %ds...",
                        operation_name,
                        attempt + 1,
                        max_retries + 1,
                        str(e),
                        sleep_seconds,
                    )
                    # 使用 time.sleep() 而非 asyncio.sleep()，因为这是同步方法。
                    # 该方法被同步的 run_collect() 调用，整个调用链都是同步的。
                    time.sleep(sleep_seconds)
                else:
                    logger.error("%s failed after %d attempts: %s", operation_name, max_retries + 1, str(e))

        raise last_exception

    def _run_collect_with_degradation(
        self, platform: str, keyword: str, max_items: int, use_degraded: bool = False
    ) -> dict[str, Any]:
        """
        执行采集，支持降级策略。

        当超时发生时，可以尝试缩减采集范围（减少滚动轮数/采集数量）后重试。
        """
        try:
            if self._use_http:
                return self._run_collect_http(platform, keyword, max_items)
            return self._run_collect_internal(platform, keyword, max_items)
        except Exception as e:
            error_str = str(e).lower()
            # 检测超时相关的错误
            is_timeout = any(
                keyword in error_str for keyword in ["timeout", "timed out", "time out", "deadline exceeded"]
            )

            if is_timeout and not use_degraded and max_items > 5:
                # 超时降级：减少采集数量后重试一次
                degraded_max_items = max(5, max_items // 2)
                logger.warning(
                    "Collection timeout with max_items=%d, degrading to max_items=%d and retrying",
                    max_items,
                    degraded_max_items,
                )
                return self._run_collect_with_degradation(platform, keyword, degraded_max_items, use_degraded=True)
            raise

    def run_collect(self, platform: str, keyword: str, max_items: int) -> dict[str, Any]:
        """执行采集，返回标准格式结果。

        使用指数退避重试机制和超时降级策略。
        """
        # 检查断路器状态
        if not self._check_circuit_breaker():
            raise RuntimeError("Circuit breaker is open - too many consecutive failures")

        # 使用指数退避重试执行采集
        return self._exponential_backoff_retry(
            operation=lambda: self._run_collect_with_degradation(platform, keyword, max_items),
            max_retries=self.DEFAULT_MAX_RETRIES,
            backoff_base=self.DEFAULT_BACKOFF_BASE_SECONDS,
            operation_name=f"collect_{platform}",
        )

    def _run_collect_http(self, platform: str, keyword: str, max_items: int) -> dict[str, Any]:
        """通过 HTTP 调用外部服务（保留向后兼容）。"""
        payload = {
            "platform": platform,
            "keyword": keyword,
            "max_items": max_items,
            "need_detail": True,
            "need_comments": False,
            "dedup": True,
            "timeout_sec": self.timeout_seconds,
        }
        url = f"{self.base_url}/api/collect/run"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def _run_collect_internal(self, platform: str, keyword: str, max_items: int) -> dict[str, Any]:
        """内部直接调用采集器，避免 HTTP 开销和 Connection refused 问题。"""
        start_ms = int(time.time() * 1000)
        req = CollectRequest(
            platform=platform,
            keyword=keyword,
            max_items=max_items,
            need_detail=True,
            need_comments=False,
            dedup=True,
            timeout_sec=self.timeout_seconds,
        )

        collector = CollectorFactory.get_collector(platform)

        # collector.collect 是同步方法
        items, stats = collector.collect(req)

        end_ms = int(time.time() * 1000)

        # 转换为与 HTTP 接口兼容的格式
        return {
            "success": True,
            "platform": platform,
            "keyword": keyword,
            "task_id": f"internal_{int(time.time())}_{uuid4().hex[:6]}",
            "count": len(items),
            "items": [item.model_dump() for item in items],
            "stats": stats.model_dump(),
            "message": "",
            "request_id": uuid4().hex,
            "cost_ms": end_ms - start_ms,
        }

    def collect_keyword(self, platform: str, keyword: str, max_items: int = 20) -> dict[str, Any]:
        """关键词采集，带重试机制。"""
        return self.run_collect(platform=platform, keyword=keyword, max_items=max_items)

    def collect_single_link(self, url: str) -> dict[str, Any]:
        """单链接采集，带重试机制。"""
        # 检查断路器状态
        if not self._check_circuit_breaker():
            raise RuntimeError("Circuit breaker is open - too many consecutive failures")

        platform = CollectService.detect_platform(url)
        if platform == "other":
            raise ValueError("暂不支持该链接平台")

        # 使用指数退避重试执行单链接采集
        return self._exponential_backoff_retry(
            operation=lambda: self._collect_single_link_with_degradation(platform, url),
            max_retries=self.DEFAULT_MAX_RETRIES,
            backoff_base=self.DEFAULT_BACKOFF_BASE_SECONDS,
            operation_name=f"collect_single_link_{platform}",
        )

    def _collect_single_link_with_degradation(self, platform: str, url: str) -> dict[str, Any]:
        """单链接采集，支持降级策略。"""
        try:
            if self._use_http:
                return self.run_collect(platform=platform, keyword=url, max_items=1)
            return self._collect_single_link_internal(platform, url)
        except Exception as e:
            error_str = str(e).lower()
            is_timeout = any(
                keyword in error_str for keyword in ["timeout", "timed out", "time out", "deadline exceeded"]
            )

            if is_timeout:
                logger.warning("Single link collection timeout for %s, will retry with shorter timeout", url)
                # 单链接采集的超时降级：使用更短的超时时间重新尝试
                # 这里通过临时修改 timeout_seconds 来实现
                original_timeout = self.timeout_seconds
                try:
                    self.timeout_seconds = min(10, original_timeout // 2)
                    if self._use_http:
                        result = self.run_collect(platform=platform, keyword=url, max_items=1)
                    else:
                        result = self._collect_single_link_internal(platform, url)
                    logger.info("Single link collection succeeded with degraded timeout")
                    return result
                finally:
                    self.timeout_seconds = original_timeout
            raise

    def _collect_single_link_internal(self, platform: str, url: str) -> dict[str, Any]:
        """内部直接调用详情采集。"""
        start_ms = int(time.time() * 1000)
        req = CollectDetailRequest(platform=platform, url=url)

        collector = CollectorFactory.get_collector(platform)
        item = collector.fetch_detail(req)

        end_ms = int(time.time() * 1000)

        return {
            "success": True,
            "platform": platform,
            "keyword": url,
            "task_id": f"internal_detail_{int(time.time())}_{uuid4().hex[:6]}",
            "count": 1,
            "items": [item.model_dump()],
            "stats": {},
            "message": "",
            "request_id": uuid4().hex,
            "cost_ms": end_ms - start_ms,
        }
