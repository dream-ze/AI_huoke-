"""核对服务器8000端口服务来源"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

commands = [
    ("docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "Docker 容器列表"),
    ("ss -lntp | grep :8000 || true", "8000 端口监听"),
    ("curl -i http://localhost:8000/health 2>/dev/null | head -n 8", "Health 响应头"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=20)
    print(f"\n=== {title} ===")
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    print(out)
    if err:
        print("stderr:", err)

ssh.close()
