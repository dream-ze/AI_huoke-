#!/usr/bin/env python3
"""
全链路联调脚本：browser_collector → 关键词采集 → 收件箱视图 → 状态流转

使用前确保：
  - backend    运行在 127.0.0.1:8000  (uvicorn main:app --reload)
  - browser_collector 运行在 127.0.0.1:8005

运行方式：
  python scripts/integration_test_pipeline.py
  python scripts/integration_test_pipeline.py --username admin --password admin123 \\
      --platform xiaohongshu --keyword 贷款 --max-items 2
"""
import argparse
import json
import sys

import httpx

BACKEND_URL = "http://127.0.0.1:8000"
COLLECTOR_URL = "http://127.0.0.1:8005"


# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────

def ok(msg: str) -> None:
    print(f"[OK]   {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", flush=True)


def dump(label: str, data) -> None:
    print(f"       {label}: {json.dumps(data, ensure_ascii=False, default=str)}", flush=True)


# ─────────────────────────────────────────
# 步骤实现
# ─────────────────────────────────────────

def step_check_services() -> None:
    print("\n[Step 1] 检查服务健康状态")
    for name, url in [("backend", f"{BACKEND_URL}/health"), ("browser_collector", f"{COLLECTOR_URL}/health")]:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code < 500:
                ok(f"{name} 响应 {r.status_code}")
            else:
                fail(f"{name} 返回 {r.status_code}，服务异常")
        except httpx.ConnectError:
            fail(f"{name} 不可达（{url}），请先启动服务")
        except Exception as exc:
            fail(f"{name} 健康检查异常: {exc}")


def step_login(username: str, password: str) -> str:
    print("\n[Step 2] 登录获取令牌")
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"登录失败 {r.status_code}: {r.text[:200]}")
    token: str = r.json()["access_token"]
    ok(f"登录成功，token 前缀={token[:20]}…")
    return token


def step_create_keyword_task(token: str, platform: str, keyword: str, max_items: int) -> dict:
    print(f"\n[Step 3] 关键词采集任务 platform={platform} keyword={keyword} max={max_items}")
    r = httpx.post(
        f"{BACKEND_URL}/api/v1/collector/tasks/keyword",
        json={"platform": platform, "keyword": keyword, "max_items": max_items},
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    if r.status_code != 200:
        fail(f"创建采集任务失败 {r.status_code}: {r.text[:300]}")
    result: dict = r.json()
    ok(f"采集任务完成")
    dump("结果", result)
    return result


def step_list_inbox(token: str, status: str = "pending") -> list:
    print(f"\n[Step 4] 查询收件箱（status={status}）")
    r = httpx.get(
        f"{BACKEND_URL}/api/v1/material/inbox",
        params={"status": status, "limit": 10},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"获取收件箱失败 {r.status_code}: {r.text[:200]}")
    items: list = r.json()
    ok(f"收件箱 {status} 条目数: {len(items)}")
    for item in items[:3]:
        dump("条目", {k: item.get(k) for k in ("id", "platform", "title", "status", "source_channel")})
    return items


def step_update_status(token: str, inbox_id: int, status: str, review_note: str) -> dict:
    print(f"\n[Step 5] 更新状态 inbox_id={inbox_id} -> {status}")
    r = httpx.patch(
        f"{BACKEND_URL}/api/v1/material/inbox/{inbox_id}/status",
        json={"status": status, "review_note": review_note},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"状态流转失败 {r.status_code}: {r.text[:300]}")
    result: dict = r.json()
    ok("状态更新成功")
    dump("结果", result)
    return result


def step_verify_status(token: str, inbox_id: int, expected_status: str) -> None:
    print(f"\n[Step 6] 验证条目已转为 {expected_status}")
    r = httpx.get(
        f"{BACKEND_URL}/api/v1/material/inbox/{inbox_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"查询详情失败 {r.status_code}")
    detail: dict = r.json()
    status = detail.get("status")
    if status != expected_status:
        fail(f"期望 {expected_status}，实际为 {status}")
    ok(f"验证通过：inbox_id={inbox_id} status={expected_status}")


# ─────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="browser_collector → 收件箱 全链路联调脚本")
    parser.add_argument("--username", default="admin", help="后台登录用户名")
    parser.add_argument("--password", default="admin123", help="后台登录密码")
    parser.add_argument("--platform", default="xiaohongshu", help="采集平台")
    parser.add_argument("--keyword", default="贷款", help="关键词")
    parser.add_argument("--max-items", type=int, default=2, dest="max_items", help="最大采集条数")
    args = parser.parse_args()

    print("=" * 56)
    print("  全链路联调：browser_collector → 收件箱 → 素材库")
    print("=" * 56)

    step_check_services()
    token = step_login(args.username, args.password)
    task_result = step_create_keyword_task(token, args.platform, args.keyword, args.max_items)

    new_count = int(task_result.get("inserted", 0)) + int(task_result.get("review", 0))
    if new_count == 0:
        warn("本次采集无新素材进入收件箱视图，跳过状态流转验证")
        print("\n[DONE] 联调结束（无可审核条目）")
        return

    pending_items = step_list_inbox(token, status="pending")
    review_items = step_list_inbox(token, status="review")
    if pending_items:
        first_id: int = pending_items[0]["id"]
        step_update_status(token, first_id, "review", "联调脚本自动转人工复核")
        step_verify_status(token, first_id, "review")
    elif review_items:
        first_id = review_items[0]["id"]
        step_update_status(token, first_id, "pending", "联调脚本自动回切待处理")
        step_verify_status(token, first_id, "pending")
    else:
        warn("pending/review 列表均为空，跳过状态流转验证")
        print("\n[DONE] 联调结束（无 pending 条目）")
        return

    print("\n" + "=" * 56)
    print("  全链路联调成功 ✓")
    print("=" * 56)


if __name__ == "__main__":
    main()
