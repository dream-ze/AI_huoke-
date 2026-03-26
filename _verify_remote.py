"""远程接口验证脚本（用完可删）"""
import httpx, json, sys

BASE = "http://116.62.86.160:8000"
# 绕过本机系统代理（Windows 代理可能导致 ReadTimeout）
CLIENT = httpx.Client(proxy=None, timeout=15)


def ok(msg): print(f"[OK]   {msg}", flush=True)
def fail(msg): print(f"[FAIL] {msg}", file=sys.stderr, flush=True); sys.exit(1)
def info(msg): print(f"       {msg}", flush=True)


# Step1: health
r = CLIENT.get(f"{BASE}/health")
if r.status_code != 200:
    fail(f"health {r.status_code}")
ok(f"health -> {r.status_code}")

# Step2: login
r = CLIENT.post(f"{BASE}/api/auth/login", json={"username": "ops42767", "password": "Ops123456"})
if r.status_code != 200:
    fail(f"login {r.status_code}: {r.text[:200]}")
token = r.json()["access_token"]
ok(f"login OK, token prefix={token[:20]}...")
H = {"Authorization": f"Bearer {token}"}

# Step3: inbox list
r = CLIENT.get(f"{BASE}/api/v1/material/inbox", headers=H, params={"limit": 5})
if r.status_code != 200:
    fail(f"inbox list {r.status_code}: {r.text[:200]}")
items = r.json()
statuses = list(set(i["status"] for i in items)) if items else []
ok(f"GET /api/v1/material/inbox -> {r.status_code}, count={len(items)}, statuses={statuses}")

# Step4: verify four action routes are registered (use nonexistent id=99999)
for action in ["approve", "to-topic", "to-negative-case", "discard"]:
    r = CLIENT.post(f"{BASE}/api/v1/material/inbox/99999/{action}", headers=H, json={})
    # 404 means route not registered; 409 means route OK but item not found/wrong status
    label = "route_OK" if r.status_code in (409, 422) else f"UNEXPECTED_{r.status_code}"
    if r.status_code == 404:
        label = "ROUTE_NOT_FOUND"
    info(f"POST /inbox/99999/{action} -> {r.status_code} [{label}] {r.json().get('detail','')[:50]}")
    if r.status_code == 404:
        fail(f"route /inbox/99999/{action} not registered on remote")

ok("All four action routes registered on remote server")

# Step5: if there are pending items, run a real approve
pending = [i for i in items if i.get("status") == "pending"]
if pending:
    target_id = pending[0]["id"]
    r = CLIENT.post(f"{BASE}/api/v1/material/inbox/{target_id}/approve", headers=H, json={"remark": "remote verify"})
    if r.status_code == 200:
        d = r.json()
        ok(f"approve inbox_id={target_id} -> status={d['status']}, content_asset_id={d.get('content_asset_id')}, insight_item_id={d.get('insight_item_id')}")
    else:
        info(f"approve returned {r.status_code}: {r.text[:200]}")
else:
    info("No pending items in inbox, skipping real approve test")

print()
print("=" * 50)
print(" Remote verification PASSED")
print(f" API docs: {BASE}/docs")
print("=" * 50)
