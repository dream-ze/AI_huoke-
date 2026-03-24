"""分步远程部署 - 每步独立执行并实时输出"""
import paramiko
import sys
import time

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"

def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWD, timeout=30)
    return ssh

def run_cmd(ssh, cmd, label="", timeout=600):
    print(f"\n--- {label} ---")
    print(f"  CMD: {cmd[:120]}")
    channel = ssh.get_transport().open_session()
    channel.settimeout(timeout)
    channel.exec_command(cmd)
    # Stream stdout
    buf = b""
    while True:
        if channel.recv_ready():
            data = channel.recv(4096)
            if data:
                text = data.decode("utf-8", errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()
                buf += data
        if channel.exit_status_ready():
            # Drain remaining
            while channel.recv_ready():
                data = channel.recv(4096)
                text = data.decode("utf-8", errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()
                buf += data
            break
        time.sleep(0.5)
    code = channel.recv_exit_status()
    # Print stderr
    while channel.recv_stderr_ready():
        err = channel.recv_stderr(4096).decode("utf-8", errors="replace")
        if err.strip():
            sys.stderr.write(err)
    print(f"\n  EXIT: {code}")
    return code

ssh = get_ssh()

print("=" * 50)
print("智获客 分步远程部署")
print("=" * 50)

# Step 1: Check Docker
run_cmd(ssh, "docker --version && docker compose version", "检查 Docker")

# Step 2: Fix line endings and permissions
run_cmd(ssh, "cd /opt/zhihuokeke/backend && sed -i 's/\\r//' deploy.sh entrypoint.sh 2>/dev/null; chmod +x deploy.sh entrypoint.sh; echo DONE", "修复权限")

# Step 3: Generate .env if needed
run_cmd(ssh, """cd /opt/zhihuokeke/backend
if [ ! -f ".env" ]; then
    echo "[INFO] 首次部署，创建 .env..."
    cp .env.server .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env
    DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    sed -i "s|^DATABASE_PASSWORD=.*|DATABASE_PASSWORD=${DB_PASS}|" .env
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:${DB_PASS}@postgres:5432/zhihuokeke|" .env
    echo "ENABLE_BOOTSTRAP_TEST_USER=False" >> .env
    echo "[OK] .env 已创建"
else
    echo "[OK] .env 已存在"
fi
""", "初始化 .env")

# Step 4: Stop old containers  
run_cmd(ssh, "cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml down 2>&1 || true", "停止旧容器")

# Step 5: Build and start (this is the long step)
run_cmd(ssh, "cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d --build 2>&1", "Docker 构建并启动", timeout=600)

# Step 6: Wait for backend
run_cmd(ssh, """
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "[OK] 后端已启动!"
        curl -s http://localhost:8000/health
        exit 0
    fi
    echo "  等待中... ($i/20)"
    sleep 3
done
echo "[WARN] 后端未在60秒内就绪"
""", "等待后端就绪")

# Step 7: Check all containers
run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态")

# Pull Ollama model in background
run_cmd(ssh, "docker compose -f /opt/zhihuokeke/backend/docker-compose.prod.yml exec -d ollama ollama pull qwen2:1.5b 2>&1 || echo '模型拉取已后台启动'", "后台拉取AI模型")

print("\n" + "=" * 50)
print("部署完成！")
print("=" * 50)
print(f"  前端页面 : http://{SERVER}:8000/")
print(f"  API 文档 : http://{SERVER}:8000/docs")
print(f"  健康检查 : http://{SERVER}:8000/health")

ssh.close()
