"""修复.env 并启动部署 - 流式输出"""
import paramiko, sys, time

SERVER = "116.62.86.160"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username="root", password="Yang@666", timeout=60, banner_timeout=60)
print("SSH 连接成功\n", flush=True)

def run(cmd, label, timeout=600):
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
        print(err.decode("utf-8", errors="replace")[-500:], flush=True)
    print(f"[exit: {code}]\n", flush=True)
    return code

# 1. 查看当前 .env 全文
run("cat /opt/zhihuokeke/backend/.env", "当前 .env 内容")

# 2. 修复 DATABASE_URL 和 DATABASE_PASSWORD
run(r"""cd /opt/zhihuokeke/backend
# 读取现有密码或生成新密码
DB_PASS=$(grep '^DATABASE_PASSWORD=' .env | cut -d= -f2-)
if [ -z "$DB_PASS" ] || [ "$DB_PASS" = "CHANGE_ME_DB_PASSWORD" ]; then
    DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    echo "生成新密码: $DB_PASS"
fi

# 修复 DATABASE_URL 为 PostgreSQL
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:${DB_PASS}@postgres:5432/zhihuokeke|" .env

# 确保 DATABASE_PASSWORD 存在且一致
if grep -q '^DATABASE_PASSWORD=' .env; then
    sed -i "s|^DATABASE_PASSWORD=.*|DATABASE_PASSWORD=${DB_PASS}|" .env
else
    echo "DATABASE_PASSWORD=${DB_PASS}" >> .env
fi

# 确保 ENVIRONMENT=production
if ! grep -q '^ENVIRONMENT=' .env; then
    echo 'ENVIRONMENT=production' >> .env
fi

echo "--- 修复后的关键配置 ---"
grep -E '^(DATABASE_URL|DATABASE_PASSWORD|SECRET_KEY|ENVIRONMENT|ENABLE_BOOTSTRAP)' .env
""", "修复 .env")

# 3. 修复权限
run("cd /opt/zhihuokeke/backend && sed -i 's/\\r//' deploy.sh entrypoint.sh && chmod +x deploy.sh entrypoint.sh && echo OK", "修复权限")

# 4. 停旧容器
run("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml down 2>&1 || true", "停止旧容器")

# 5. 构建并启动
run("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml up -d --build 2>&1", "Docker 构建启动", timeout=600)

# 6. 等待后端就绪
run("""for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health 2>/dev/null; then
        echo ""
        echo "后端已就绪!"
        exit 0
    fi
    echo "等待后端... ($i/30)"
    sleep 3
done
echo "超时！查看日志:"
docker logs zhihuokeke-backend --tail 50 2>&1
""", "等待后端就绪", timeout=120)

# 7. 最终状态
run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态")

print(f"""
{'='*50}
  前端页面 : http://{SERVER}:8000/
  API 文档 : http://{SERVER}:8000/docs
  健康检查 : http://{SERVER}:8000/health
{'='*50}
""", flush=True)

ssh.close()
