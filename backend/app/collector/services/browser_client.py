from typing import Any
import asyncio
import time
from uuid import uuid4

import httpx

from app.core.config import settings
from app.collector.services.collect_service import CollectService
from app.collector.parsers.xiaohongshu import XiaohongshuCollector
from app.schemas.request import CollectRequest
from app.schemas.detail import CollectDetailRequest


class BrowserCollectorClient:
    """Client for browser_collector internal service.
    
    默认使用内部直接调用模式（不再依赖 HTTP 外部服务）。
    如果设置了 BROWSER_COLLECTOR_BASE_URL 且不是 127.0.0.1，则回退到 HTTP 调用。
    """

    def __init__(self, *, use_http: bool = False) -> None:
        self.base_url = settings.BROWSER_COLLECTOR_BASE_URL.rstrip("/")
        self.timeout_seconds = settings.BROWSER_COLLECTOR_TIMEOUT_SECONDS
        # 默认使用内部调用，除非显式指定 use_http 或 URL 不是本地地址
        self._use_http = use_http or not self._is_local_url()
        
    def _is_local_url(self) -> bool:
        """检查是否是本地地址（127.0.0.1 或 localhost）"""
        return "127.0.0.1" in self.base_url or "localhost" in self.base_url

    def run_collect(self, platform: str, keyword: str, max_items: int) -> dict[str, Any]:
        """执行采集，返回标准格式结果。"""
        if self._use_http:
            return self._run_collect_http(platform, keyword, max_items)
        return self._run_collect_internal(platform, keyword, max_items)

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
        if platform != "xiaohongshu":
            raise ValueError(f"暂不支持平台: {platform}")
        
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
        
        collector = XiaohongshuCollector()
        
        # XiaohongshuCollector.collect 是同步方法
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
        return self.run_collect(platform=platform, keyword=keyword, max_items=max_items)

    def collect_single_link(self, url: str) -> dict[str, Any]:
        platform = CollectService.detect_platform(url)
        if platform == "other":
            raise ValueError("暂不支持该链接平台")
        
        if self._use_http:
            return self.run_collect(platform=platform, keyword=url, max_items=1)
        
        
        # 内部调用详情采集
        return self._collect_single_link_internal(platform, url)
    
    def _collect_single_link_internal(self, platform: str, url: str) -> dict[str, Any]:
        """内部直接调用详情采集。"""
        if platform != "xiaohongshu":
            raise ValueError(f"暂不支持平台: {platform}")
        
        start_ms = int(time.time() * 1000)
        req = CollectDetailRequest(platform=platform, url=url)
        
        collector = XiaohongshuCollector()
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
