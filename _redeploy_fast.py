"""快速重部署：仅上传Dockerfile并重建backend"""
import paramiko
import time

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"
LOCAL_DOCKERFILE = r"D:\智获客\backend\Dockerfile"
REMOTE_DOCKERFILE = "/opt/zhihuokeke/backend/Dockerfile"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=60, banner_timeout=60)
sftp = ssh.open_sftp()

print("[1/4] 上传优化后的 Dockerfile...")
sftp.put(LOCAL_DOCKERFILE, REMOTE_DOCKERFILE)
print("  OK")

print("[2/4] 停止旧的后台构建任务...")
ssh.exec_command("pkill -f 'docker compose -f docker-compose.prod.yml up -d --build' 2>/dev/null || true")
ssh.exec_command("pkill -f '/tmp/deploy.log' 2>/dev/null || true")
time.sleep(1)
print("  OK")

print("[3/4] 重新后台构建 backend（日志写入 /tmp/deploy_fast.log）...")
cmd = r"""cd /opt/zhihuokeke/backend
nohup bash -c '
  docker compose -f docker-compose.prod.yml up -d --build backend 2>&1
  echo "FAST_BUILD_DONE at $(date)"
' > /tmp/deploy_fast.log 2>&1 &
echo PID:$!
"""
_, out, err = ssh.exec_command(cmd, timeout=15)
print(out.read().decode("utf-8", errors="replace").strip())
e = err.read().decode("utf-8", errors="replace").strip()
if e:
    print("ERR:", e)

print("[4/4] 输出快速检查命令")
print("  查看进度: python _deploy_check_fast.py")
print("  访问地址: http://116.62.86.160:8000/health")

sftp.close()
ssh.close()
