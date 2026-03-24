"""修复后端环境变量并重启服务"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

commands = [
    ("sed -i '/^ENVIRONMENT=/d' /opt/zhihuokeke/backend/.env", "删除ENVIRONMENT配置"),
    ("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d backend", "重启backend"),
    ("docker logs zhihuokeke-backend --tail 60 2>&1", "backend日志"),
    ("curl -sf http://localhost:8000/health 2>/dev/null || echo '后端未就绪'", "健康检查"),
    ("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=45)
    print(f"\n=== {title} ===")
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out)
    if err:
        print("stderr:", err)

ssh.close()
