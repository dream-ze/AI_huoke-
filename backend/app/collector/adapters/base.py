import asyncio
from abc import ABC, abstractmethod
from typing import Any, Tuple

from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem


class BaseCollector(ABC):
    """
    Base class for all platform collectors.

    Provides common functionality including anti-detection hooks,
    retry policies, and standardized collection interface.
    """

    def __init__(self) -> None:
        """Initialize base collector with retry policy."""
        self.retry_policy = {
            "max_retries": 3,
            "base_delay": 2.0,
        }

    @abstractmethod
    def collect(self, req: CollectRequest) -> Tuple[list[ContentItem], CollectStats]:
        """Collect content items based on request parameters."""
        raise NotImplementedError

    @abstractmethod
    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        """Fetch detailed information for a specific content item."""
        raise NotImplementedError

    def _run_async(self, coro: Any) -> Any:
        """Helper to run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in an event loop, use run_coroutine_threadsafe
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(coro)

    def before_navigate(self, page) -> None:
        """
        Hook called before navigating to a page (sync version).

        Default implementation applies stealth modifications and sets
        a random User-Agent to evade bot detection.

        Args:
            page: Playwright page instance (sync or async)
        """
        from app.collector.utils.anti_detect import get_random_ua

        # Check if page is async or sync
        if hasattr(page, "add_init_script"):
            # Sync page - apply stealth via script injection
            page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer2",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
                delete navigator.__proto__.webdriver;
            """
            )
            page.set_extra_http_headers({"User-Agent": get_random_ua()})

    def after_navigate(self, page) -> None:
        """
        Hook called after navigating to a page (sync version).

        Default implementation injects a random delay to simulate
        human browsing behavior.

        Args:
            page: Playwright page instance (sync or async)
        """
        import random
        import time

        delay = random.uniform(1.0, 3.0)
        # 使用 time.sleep() 而非 asyncio.sleep()，因为这是同步版本。
        # 对应的异步版本请使用 after_navigate_async()。
        time.sleep(delay)

    async def before_navigate_async(self, page) -> None:
        """
        Hook called before navigating to a page (async version).

        Default implementation applies stealth modifications and sets
        a random User-Agent to evade bot detection.

        Args:
            page: Playwright async page instance
        """
        from app.collector.utils.anti_detect import apply_stealth, get_random_ua

        await apply_stealth(page)
        await page.set_extra_http_headers({"User-Agent": get_random_ua()})

    async def after_navigate_async(self, page) -> None:
        """
        Hook called after navigating to a page (async version).

        Default implementation injects a random delay to simulate
        human browsing behavior.

        Args:
            page: Playwright async page instance
        """
        from app.collector.utils.anti_detect import random_delay

        await random_delay()
