"""查看快速重部署进度"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

cmds = [
    ("tail -80 /tmp/deploy_fast.log 2>/dev/null || echo '暂无日志'", "快速构建日志"),
    ("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态"),
    ("curl -sf http://localhost:8000/health 2>/dev/null || echo '后端未就绪'", "健康检查"),
]

for cmd, title in cmds:
    _, o, e = ssh.exec_command(cmd, timeout=15)
    print(f"\n=== {title} ===")
    print(o.read().decode("utf-8", errors="replace").strip())
    err = e.read().decode("utf-8", errors="replace").strip()
    if err:
        print(f"stderr: {err[:200]}")

ssh.close()
