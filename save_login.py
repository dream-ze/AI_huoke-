"""
一次性登录脚本。
运行后浏览器弹出，手动扫码或账密登录小红书，
登录成功后回到终端按 Enter，会话自动保存到 xiaohongshu_state.json。
"""
import pathlib
from playwright.sync_api import sync_playwright

STATE_PATH = pathlib.Path(__file__).parent / "xiaohongshu_state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = context.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")

        print("\n浏览器已打开小红书。")
        print("请手动完成登录（扫码 或 账密+验证码）。")
        print("登录成功后，回到此终端，按 Enter 保存会话...\n")
        input()

        context.storage_state(path=str(STATE_PATH))
        print(f"会话已保存至 {STATE_PATH}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
