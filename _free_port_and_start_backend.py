"""释放8000端口并启动容器backend"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

commands = [
    ("ss -lntp | grep :8000 || true", "当前8000占用"),
    ("PID=$(ss -lntp | awk '/:8000/{print $NF}' | sed -n 's/.*pid=\\([0-9]\\+\\).*/\\1/p' | head -n1); if [ -n \"$PID\" ]; then kill -9 $PID && echo killed:$PID; else echo no_pid; fi", "释放8000端口"),
    ("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d backend", "启动backend容器"),
    ("sleep 3; docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态"),
    ("for i in $(seq 1 20); do curl -sf http://localhost:8000/health && exit 0; sleep 2; done; echo '后端未就绪'", "健康检查"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=90)
    print(f"\n=== {title} ===")
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out)
    if err:
        print("stderr:", err)

ssh.close()
