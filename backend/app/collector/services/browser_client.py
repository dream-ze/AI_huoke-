from typing import Any

import httpx

from app.core.config import settings
from app.collector.services.collect_service import CollectService


class BrowserCollectorClient:
    """Client for browser_collector internal service."""

    def __init__(self) -> None:
        self.base_url = settings.BROWSER_COLLECTOR_BASE_URL.rstrip("/")
        self.timeout_seconds = settings.BROWSER_COLLECTOR_TIMEOUT_SECONDS

    def run_collect(self, platform: str, keyword: str, max_items: int) -> dict[str, Any]:
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

    def collect_keyword(self, platform: str, keyword: str, max_items: int = 20) -> dict[str, Any]:
        return self.run_collect(platform=platform, keyword=keyword, max_items=max_items)

    def collect_single_link(self, url: str) -> dict[str, Any]:
        platform = CollectService.detect_platform(url)
        if platform == "other":
            raise ValueError("暂不支持该链接平台")
        return self.run_collect(platform=platform, keyword=url, max_items=1)
