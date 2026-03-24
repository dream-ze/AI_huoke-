"""上传entrypoint热修复并恢复容器运行"""
import paramiko

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"

LOCAL_ENTRYPOINT = r"D:\智获客\backend\entrypoint.sh"
REMOTE_ENTRYPOINT = "/opt/zhihuokeke/backend/entrypoint.sh"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=60, banner_timeout=60)
sftp = ssh.open_sftp()

print("[1/5] 上传 entrypoint 热修复...")
sftp.put(LOCAL_ENTRYPOINT, REMOTE_ENTRYPOINT)
print("  OK")

print("[2/5] 修复脚本权限与换行...")
_, o, e = ssh.exec_command("sed -i 's/\\r//' /opt/zhihuokeke/backend/entrypoint.sh && chmod +x /opt/zhihuokeke/backend/entrypoint.sh", timeout=20)
print(o.read().decode("utf-8", errors="replace").strip())
err = e.read().decode("utf-8", errors="replace").strip()
if err:
    print("stderr:", err)

print("[3/5] 释放 8000 端口残留进程...")
cmd_kill = "PID=$(ss -lntp | awk '/:8000/{print $NF}' | sed -n 's/.*pid=\\([0-9]\\+\\).*/\\1/p' | head -n1); if [ -n \"$PID\" ]; then kill -9 $PID && echo killed:$PID; else echo no_pid; fi"
_, o, e = ssh.exec_command(cmd_kill, timeout=20)
print(o.read().decode("utf-8", errors="replace").strip())
err = e.read().decode("utf-8", errors="replace").strip()
if err:
    print("stderr:", err)

print("[4/5] 重建并启动 backend...")
_, o, e = ssh.exec_command("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d --build backend", timeout=300)
out = o.read().decode("utf-8", errors="replace")
err = e.read().decode("utf-8", errors="replace")
if out.strip():
    print(out[-2500:])
if err.strip():
    print("stderr:\n" + err[-1200:])

print("[5/5] 健康检查 + 最新日志...")
_, o, _ = ssh.exec_command("for i in $(seq 1 30); do curl -sf http://localhost:8000/health && exit 0; sleep 2; done; echo '后端未就绪'", timeout=80)
print("health:", o.read().decode("utf-8", errors="replace").strip())

_, o, _ = ssh.exec_command("docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", timeout=20)
print(o.read().decode("utf-8", errors="replace").strip())

_, o, _ = ssh.exec_command("docker logs zhihuokeke-backend --tail 60 2>&1", timeout=20)
print("\n--- backend logs (tail 60) ---")
print(o.read().decode("utf-8", errors="replace"))

sftp.close()
ssh.close()
