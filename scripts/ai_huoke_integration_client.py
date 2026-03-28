from __future__ import annotations

from typing import Any

import requests


class BrowserCollectorClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8005", timeout: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def collect_content(
        self,
        keyword: str,
        max_items: int = 10,
        need_detail: bool = True,
        need_comments: bool = False,
        dedup: bool = True,
        timeout_sec: int = 120,
    ) -> dict[str, Any]:
        payload = {
            "platform": "xiaohongshu",
            "keyword": keyword,
            "max_items": max_items,
            "need_detail": need_detail,
            "need_comments": need_comments,
            "dedup": dedup,
            "timeout_sec": timeout_sec,
        }
        resp = requests.post(
            f"{self.base_url}/api/collect/run",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def collect_detail(self, url: str | None = None, source_id: str | None = None) -> dict[str, Any]:
        payload = {"platform": "xiaohongshu", "url": url, "source_id": source_id}
        resp = requests.post(
            f"{self.base_url}/api/collect/detail",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    client = BrowserCollectorClient(base_url="http://127.0.0.1:8005", timeout=240)
    print("health:", client.health())

    result = client.collect_content(
        keyword="贷款",
        max_items=10,
        need_detail=True,
        need_comments=True,
        dedup=True,
        timeout_sec=180,
    )
    print("count:", result.get("count"))
    print("request_id:", result.get("request_id"))
