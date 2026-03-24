"""上传配置修复并快速重建 backend"""
import paramiko

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"

LOCAL_FILE = r"D:\智获客\backend\app\core\config.py"
REMOTE_FILE = "/opt/zhihuokeke/backend/app/core/config.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=60, banner_timeout=60)
sftp = ssh.open_sftp()

print("[1/3] 上传 config.py 修复...")
sftp.put(LOCAL_FILE, REMOTE_FILE)
print("  OK")

print("[2/3] 重建并启动 backend...")
cmd = "cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d --build backend"
_, o, e = ssh.exec_command(cmd, timeout=240)
out = o.read().decode("utf-8", errors="replace")
err = e.read().decode("utf-8", errors="replace")
print(out[-3000:])
if err.strip():
    print("stderr:\n" + err[-1200:])

print("[3/3] 检查健康状态...")
_, o, _ = ssh.exec_command("for i in $(seq 1 20); do curl -sf http://localhost:8000/health && exit 0; sleep 2; done; echo '后端未就绪'", timeout=50)
print(o.read().decode("utf-8", errors="replace"))

_, o, _ = ssh.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", timeout=15)
print(o.read().decode("utf-8", errors="replace"))

sftp.close()
ssh.close()
