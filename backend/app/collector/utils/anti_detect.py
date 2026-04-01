"""
Anti-detection utilities for web scraping.

Provides tools to evade common bot detection mechanisms:
- User-Agent rotation
- Random delay injection
- Cookie/Session management
- Browser fingerprint stealth
"""

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any

from playwright.async_api import Page

logger = logging.getLogger(__name__)

# User-Agent pool with real browser strings
USER_AGENT_POOL = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


def get_random_ua() -> str:
    """
    Get a random User-Agent from the pool.

    Returns:
        A random User-Agent string from real browsers.
    """
    return random.choice(USER_AGENT_POOL)


async def random_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """
    Inject a random delay between operations.

    Args:
        min_s: Minimum delay in seconds (default: 1.0)
        max_s: Maximum delay in seconds (default: 3.0)
    """
    delay = random.uniform(min_s, max_s)
    logger.debug(f"Injecting random delay: {delay:.2f}s")
    await asyncio.sleep(delay)


class CookieManager:
    """
    Manager for cookie persistence and loading.

    Provides save/load functionality for cookies to maintain
    session state across scraping sessions.

    Attributes:
        storage_dir: Directory to store cookie files
    """

    def __init__(self, storage_dir: str | Path = ".cookies") -> None:
        """
        Initialize CookieManager.

        Args:
            storage_dir: Directory path for cookie storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"CookieManager initialized with storage: {self.storage_dir}")

    def _get_cookie_path(self, domain: str) -> Path:
        """Get the file path for a domain's cookies."""
        # Sanitize domain for filename
        safe_domain = domain.replace(".", "_").replace(":", "_")
        return self.storage_dir / f"{safe_domain}.json"

    async def save_cookies(self, page: Page, domain: str) -> None:
        """
        Save cookies from a page to storage.

        Args:
            page: Playwright page instance
            domain: Domain identifier for the cookies
        """
        try:
            cookies = await page.context.cookies()
            cookie_path = self._get_cookie_path(domain)
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies for domain: {domain}")
        except Exception as e:
            logger.warning(f"Failed to save cookies for {domain}: {e}")

    async def load_cookies(self, context: Any, domain: str) -> bool:
        """
        Load cookies from storage into a browser context.

        Args:
            context: Playwright browser context
            domain: Domain identifier for the cookies

        Returns:
            True if cookies were loaded, False otherwise
        """
        cookie_path = self._get_cookie_path(domain)
        if not cookie_path.exists():
            logger.debug(f"No saved cookies found for domain: {domain}")
            return False

        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            logger.info(f"Loaded {len(cookies)} cookies for domain: {domain}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load cookies for {domain}: {e}")
            return False

    def clear_cookies(self, domain: str | None = None) -> None:
        """
        Clear stored cookies.

        Args:
            domain: Specific domain to clear, or None to clear all
        """
        if domain:
            cookie_path = self._get_cookie_path(domain)
            if cookie_path.exists():
                cookie_path.unlink()
                logger.info(f"Cleared cookies for domain: {domain}")
        else:
            for cookie_file in self.storage_dir.glob("*.json"):
                cookie_file.unlink()
            logger.info("Cleared all stored cookies")


async def apply_stealth(page: Page) -> None:
    """
    Apply stealth modifications to evade bot detection.

    Modifies common detection points:
    - navigator.webdriver
    - navigator.plugins
    - navigator.languages
    - Webdriver property

    Args:
        page: Playwright page instance to modify
    """
    logger.debug("Applying stealth modifications to page")

    # Inject stealth script
    await page.add_init_script(
        """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Mock plugins
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
                },
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer3",
                    length: 1,
                    name: "Native Client"
                }
            ]
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        
        // Remove automation indicators
        delete navigator.__proto__.webdriver;
        
        // Mock chrome runtime
        if (window.chrome) {
            window.chrome.runtime = {
                OnInstalledReason: {CHROME_UPDATE: "chrome_update", INSTALL: "install", SHARED_MODULE_UPDATE: "shared_module_update", UPDATE: "update"},
                OnRestartRequiredReason: {APP_UPDATE: "app_update", OS_UPDATE: "os_update", PERIODIC: "periodic"},
                PlatformArch: {ARM: "arm", ARM64: "arm64", MIPS: "mips", MIPS64: "mips64", MIPS64EL: "mips64el", MIPSEL: "mipsel", X86_32: "x86-32", X86_64: "x86-64"},
                PlatformNaclArch: {ARM: "arm", MIPS: "mips", MIPS64: "mips64", MIPS64EL: "mips64el", MIPSEL: "mipsel", MIPSEL64: "mipsel64", X86_32: "x86-32", X86_64: "x86-64"},
                PlatformOs: {ANDROID: "android", CROS: "cros", LINUX: "linux", MAC: "mac", OPENBSD: "openbsd", WIN: "win"},
                RequestUpdateCheckStatus: {NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available"}
            };
        }
        
        // Mock notification permission
        const originalQuery = window.Notification.requestPermission;
        window.Notification.requestPermission = function(callback) {
            if (callback) callback('default');
            return Promise.resolve('default');
        };
        
        // Override permission query
        const originalPermissions = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({
                    state: 'prompt',
                    onchange: null,
                    addEventListener: function() {},
                    removeEventListener: function() {}
                });
            }
            return originalPermissions.call(navigator.permissions, parameters);
        };
        
        // Hide automation from iframe
        if (window.self !== window.top) {
            Object.defineProperty(window, 'navigator', {
                value: new Proxy(navigator, {
                    has: (target, key) => (key === 'webdriver' ? false : key in target),
                    get: (target, key) => key === 'webdriver' ? undefined : target[key]
                })
            });
        }
    """
    )

    logger.debug("Stealth modifications applied successfully")
