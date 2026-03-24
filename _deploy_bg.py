"""后台启动Docker构建（nohup），不怕SSH断开"""
import paramiko, sys, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=60, banner_timeout=60)
print("SSH 连接成功\n", flush=True)

def run(cmd, label, timeout=30):
    print(f"=== {label} ===", flush=True)
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    while True:
        if chan.recv_ready():
            sys.stdout.write(chan.recv(4096).decode("utf-8", errors="replace"))
            sys.stdout.flush()
        if chan.exit_status_ready():
            while chan.recv_ready():
                sys.stdout.write(chan.recv(4096).decode("utf-8", errors="replace"))
                sys.stdout.flush()
            break
        time.sleep(0.3)
    code = chan.recv_exit_status()
    err = b""
    while chan.recv_stderr_ready():
        err += chan.recv_stderr(4096)
    if err.strip():
        print(err.decode("utf-8", errors="replace")[-300:], flush=True)
    print(f"[exit: {code}]\n", flush=True)
    return code

# 1. 检查是否有正在进行的构建
run("docker ps -a --format '{{.Names}} {{.Status}}' 2>&1; pgrep -fa 'docker build' 2>&1 || echo '无构建进程'", "当前状态")

# 2. 验证 .env 已修复
run("grep '^DATABASE_URL=' /opt/zhihuokeke/backend/.env", "检查 DATABASE_URL")

# 3. 用 nohup 在后台启动构建（日志写到文件）
run("""cd /opt/zhihuokeke/backend
nohup bash -c '
  docker compose -f docker-compose.prod.yml down 2>&1
  docker compose -f docker-compose.prod.yml up -d --build 2>&1
  echo "BUILD_DONE at $(date)"
' > /tmp/deploy.log 2>&1 &
echo "后台构建已启动, PID: $!"
echo "查看进度: tail -f /tmp/deploy.log"
""", "启动后台构建")

print("""
构建已在服务器后台运行，不受SSH断开影响。
查看进度请运行: python _deploy_check.py
""", flush=True)

ssh.close()
