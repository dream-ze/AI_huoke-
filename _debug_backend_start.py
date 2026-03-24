"""前台启动backend获取实时报错"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

cmd = "cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up backend --no-deps 2>&1"
chan = ssh.get_transport().open_session()
chan.settimeout(120)
chan.exec_command(cmd)

start = time.time()
print("=== 前台启动backend（采样60秒）===")
while time.time() - start < 60:
    if chan.recv_ready():
        print(chan.recv(4096).decode("utf-8", errors="replace"), end="")
    if chan.exit_status_ready():
        break
    time.sleep(0.2)

if not chan.exit_status_ready():
    chan.close()

print("\n=== 结束采样，补充最近日志 ===")
_, o, _ = ssh.exec_command("docker logs zhihuokeke-backend --tail 120 2>&1", timeout=20)
print(o.read().decode("utf-8", errors="replace"))

ssh.close()
