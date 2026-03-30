from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:5173"
OUTPUT_DIR = Path(r"d:\智获客\temp\e2e-artifacts")


def save_screenshot(page, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUTPUT_DIR / name), full_page=True)


def create_material_via_browser_api(page, title: str, content: str) -> dict:
    return page.evaluate(
        """
        async ({ title, content }) => {
          const token = localStorage.getItem('zhk_token');
          const response = await fetch('/api/mvp/materials', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              platform: 'xiaohongshu',
              title,
              content,
              source_url: 'https://example.com/e2e-smoke',
              author: 'e2e-smoke',
            }),
          });
          const text = await response.text();
          try {
            return { ok: response.ok, status: response.status, data: JSON.parse(text) };
          } catch {
            return { ok: response.ok, status: response.status, data: { raw: text } };
          }
        }
        """,
        {"title": title, "content": content},
    )


def login(page) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    inputs = page.locator("input")
    inputs.nth(0).fill("testuser")
    inputs.nth(1).fill("password123")
    page.get_by_role("button", name="登录").click()
    page.wait_for_url(lambda url: not str(url).endswith("/login"), timeout=30000)


def run_generate(page) -> dict:
    page.goto(f"{BASE_URL}/mvp-workbench", wait_until="networkidle")
    save_screenshot(page, "01-workbench-before-generate.png")

    local_model = page.get_by_role("button", name="💻 本地模型")
    if local_model.count() > 0:
        local_model.click()

    page.get_by_role("button", name="🚀 开始生成").click()

    try:
        page.get_by_text("⭐ 最终推荐文案").wait_for(timeout=240000)
        save_screenshot(page, "02-workbench-after-generate.png")
        final_text = page.get_by_text("⭐ 最终推荐文案").locator("xpath=following::*[1]").inner_text()
        return {
            "success": True,
            "message": "开始生成并完成返回",
            "snippet": final_text[:500],
        }
    except PlaywrightTimeoutError:
        save_screenshot(page, "02-workbench-generate-timeout-or-error.png")
        error_box = page.get_by_text("⚠️ 生成失败")
        if error_box.count() > 0:
            return {
                "success": False,
                "message": error_box.locator("xpath=..").inner_text(),
            }
        body_text = page.locator("body").inner_text()
        return {
            "success": False,
            "message": "开始生成在超时时间内未完成返回",
            "snippet": body_text[:800],
        }


def ensure_materials(page) -> list[dict]:
    page.goto(f"{BASE_URL}/mvp-materials", wait_until="networkidle")
    created = []
    if page.get_by_text("素材库为空").count() > 0:
        timestamp = page.evaluate("Date.now()")
        for index in range(2):
            created.append(
                create_material_via_browser_api(
                    page,
                    f"E2E素材-{timestamp}-{index + 1}",
                    f"这是用于端到端验证的测试素材内容 {index + 1}，用于执行批量入知识库操作。",
                )
            )
        page.reload(wait_until="networkidle")
    return created


def run_batch_build_knowledge(page) -> dict:
    created = ensure_materials(page)
    save_screenshot(page, "03-materials-before-batch-build.png")

    row_checkboxes = page.locator("tbody input[type='checkbox']")
    checkbox_count = row_checkboxes.count()
    if checkbox_count == 0:
        return {
            "success": False,
            "message": "素材页没有可选择的数据，无法执行批量入知识库",
            "created": created,
        }

    row_checkboxes.nth(0).check()
    if checkbox_count > 1:
        row_checkboxes.nth(1).check()

    page.get_by_role("button", name="📚 批量入知识库").click()
    page.locator(".mat-message").wait_for(timeout=180000)
    save_screenshot(page, "04-materials-after-batch-build.png")

    return {
        "success": True,
        "message": page.locator(".mat-message").inner_text(),
        "created": created,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "baseUrl": BASE_URL,
        "generate": None,
        "batchBuildKnowledge": None,
    }

    browser_executable = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=browser_executable)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        try:
            login(page)
            save_screenshot(page, "00-after-login.png")
            summary["generate"] = run_generate(page)
            summary["batchBuildKnowledge"] = run_batch_build_knowledge(page)
        finally:
            browser.close()

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())