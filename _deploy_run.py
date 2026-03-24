"""简化版分步部署 - 文件已上传，仅执行远程部署命令"""
import paramiko, sys, time

SERVER = "116.62.86.160"
USER = "root"  
PASSWD = "Yang@666"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=60, banner_timeout=60, auth_timeout=60)
print("SSH 连接成功", flush=True)

def run(cmd, label, timeout=600):
    print(f"\n=== {label} ===", flush=True)
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
    print(f"[exit: {code}]", flush=True)
    return code

# 1. 检查 Docker
run("docker --version && docker compose version", "检查 Docker")

# 2. 修复权限 + 生成 .env
run("""cd /opt/zhihuokeke/backend
sed -i 's/\\r//' deploy.sh entrypoint.sh 2>/dev/null
chmod +x deploy.sh entrypoint.sh
ls -la *.sh *.yml .env* 2>/dev/null
""", "修复文件权限")

run("""cd /opt/zhihuokeke/backend
if [ ! -f ".env" ]; then
    cp .env.server .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" .env
    DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    sed -i "s|^DATABASE_PASSWORD=.*|DATABASE_PASSWORD=$DB_PASS|" .env
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:${DB_PASS}@postgres:5432/zhihuokeke|" .env
    grep -q ENABLE_BOOTSTRAP_TEST_USER .env || echo 'ENABLE_BOOTSTRAP_TEST_USER=False' >> .env
    echo '.env 已创建并初始化'
else
    echo '.env 已存在'
fi
""", "初始化环境变量")

# 3. 停止旧容器
run("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml down 2>&1 || true", "停止旧容器")

# 4. Docker 构建并启动（重点步骤）
run("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d --build 2>&1", "Docker 构建启动", timeout=600)

# 5. 等待后端就绪
run("""for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health 2>/dev/null; then
        echo ""
        echo "后端已就绪!"
        exit 0
    fi
    echo "等待后端... ($i/30)"
    sleep 3
done
echo "超时，检查日志..."
docker logs zhihuokeke-backend --tail 30 2>&1
""", "等待后端就绪", timeout=120)

# 6. 查看容器状态
run("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", "容器状态")

# 后台拉取模型
run("docker exec -d zhihuokeke-ollama ollama pull qwen2:1.5b 2>&1; echo '模型拉取已在后台启动'", "后台拉取AI模型")

print(f"""
{'='*50}
 部署完成！访问链接：
{'='*50}
  前端页面 : http://{SERVER}:8000/
  API 文档 : http://{SERVER}:8000/docs  
  健康检查 : http://{SERVER}:8000/health
{'='*50}
""", flush=True)

ssh.close()
