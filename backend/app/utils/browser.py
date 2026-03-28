import pathlib
from playwright.sync_api import sync_playwright
from app.core.config import settings

STATE_PATH = pathlib.Path(__file__).parent.parent.parent / "xiaohongshu_state.json"


def create_browser():
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=settings.BROWSER_HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    state_file = str(STATE_PATH) if STATE_PATH.exists() else None

    context = browser.new_context(
        viewport={
            "width": settings.BROWSER_VIEWPORT_WIDTH,
            "height": settings.BROWSER_VIEWPORT_HEIGHT,
        },
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        ),
        locale="zh-CN",
        storage_state=state_file,
    )

    page = context.new_page()
    page.set_default_timeout(settings.BROWSER_TIMEOUT_MS)

    return playwright, browser, context, page
