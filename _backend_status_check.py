"""检查backend稳定性"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

commands = [
    ("docker inspect zhihuokeke-backend --format 'RestartCount={{.RestartCount}} State={{.State.Status}} StartedAt={{.State.StartedAt}} FinishedAt={{.State.FinishedAt}}'", "容器状态详情"),
    ("grep '^CORS_ORIGINS=' /opt/zhihuokeke/backend/.env", "CORS配置"),
    ("docker logs zhihuokeke-backend --tail 40 2>&1", "最新日志"),
    ("curl -sf http://localhost:8000/health 2>/dev/null || echo '后端未就绪'", "健康检查"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=20)
    print(f"\n=== {title} ===")
    print(o.read().decode("utf-8", errors="replace").strip())
    err = e.read().decode("utf-8", errors="replace").strip()
    if err:
        print("stderr:", err)

ssh.close()
