#!/bin/bash
# ============================================================
# 智获客 - 服务器端部署脚本
# 在服务器 (116.62.86.160) 上执行:
#   bash /opt/zhihuokeke/backend/deploy.sh
#
# 前置条件: Docker 已安装
# ============================================================
set -e

DEPLOY_DIR="/opt/zhihuokeke/backend"

echo "====================================="
echo " 智获客 - 服务器部署 v1.0"
echo " 服务器: 116.62.86.160"
echo "====================================="

# ── 检查 Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "[错误] Docker 未安装，请先安装 Docker"
    echo "  curl -fsSL https://get.docker.com | bash"
    exit 1
fi
echo "[OK] Docker: $(docker --version)"

cd "$DEPLOY_DIR"

# ── 生成 .env（首次部署）────────────────────────────────
if [ ! -f ".env" ]; then
    echo "[INFO] 首次部署，从 .env.server 创建 .env..."
    cp .env.server .env

    # 自动生成随机 SECRET_KEY
    if grep -q '^SECRET_KEY=CHANGE_ME_SECRET_KEY_MIN_32_CHARS' .env; then
        SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env
        echo "[OK] SECRET_KEY 已随机生成"
    fi

    # 自动生成随机数据库口令并同步 DATABASE_URL
    if grep -q '^DATABASE_PASSWORD=CHANGE_ME_DB_PASSWORD' .env; then
        DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
        sed -i "s|^DATABASE_PASSWORD=.*|DATABASE_PASSWORD=${DB_PASS}|" .env
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:${DB_PASS}@postgres:5432/zhihuokeke|" .env
        echo "[OK] DATABASE_PASSWORD 已随机生成"
    fi

    # 生产默认不创建测试用户
    if ! grep -q '^ENABLE_BOOTSTRAP_TEST_USER=' .env; then
        echo 'ENABLE_BOOTSTRAP_TEST_USER=False' >> .env
    fi

    echo "[OK] .env 已创建并完成安全初始化"
else
    echo "[OK] .env 已存在，跳过创建"
fi

# ── 修复 entrypoint.sh 行尾（Windows CRLF → LF）────────
sed -i 's/\r//' entrypoint.sh
chmod +x entrypoint.sh

# ── 释放 8000 端口占用（避免宿主机残留 python 进程抢占）────
PORT_8000_PID=$(ss -lntp 2>/dev/null | awk '/:8000/{print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1)
if [ -n "$PORT_8000_PID" ]; then
    echo "[WARN] 检测到 8000 端口占用，尝试释放（PID=$PORT_8000_PID）..."
    kill -9 "$PORT_8000_PID" 2>/dev/null || true
    sleep 1
fi

# ── 启动服务 ────────────────────────────────────────────
echo ""
echo "[1/3] 停止旧容器..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

echo "[2/3] 构建镜像并启动..."
docker compose -f docker-compose.prod.yml up -d --build

echo "[3/3] 等待后端就绪..."
READY=0
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "[OK] 后端已启动！"
        READY=1
        break
    fi
    echo "  等待中... ($i/30)"
    sleep 3
done

if [ "$READY" -ne 1 ]; then
    echo "[ERROR] 后端健康检查超时，输出最近日志："
    docker compose -f docker-compose.prod.yml logs --tail 120 backend || true
    exit 1
fi

# ── 拉取 AI 模型（后台异步）──────────────────────────────
echo ""
echo "[INFO] 后台拉取 Ollama 模型 qwen2:1.5b（约 1GB，需几分钟）..."
docker compose -f docker-compose.prod.yml exec -d ollama \
    ollama pull qwen2:1.5b 2>/dev/null || \
    echo "[注意] 可手动执行: docker exec zhihuokeke-ollama ollama pull qwen2:1.5b"

# ── 完成 ────────────────────────────────────────────────
echo ""
echo "====================================="
echo " 部署完成！"
echo "====================================="
echo ""
echo "  API 地址 : http://116.62.86.160:8000"
echo "  API 文档 : http://116.62.86.160:8000/docs"
echo "  健康检查 : http://116.62.86.160:8000/health"
echo ""
echo "  查看日志 : docker compose -f docker-compose.prod.yml logs -f backend"
echo "  停止服务 : docker compose -f docker-compose.prod.yml down"
echo "  重启服务 : docker compose -f docker-compose.prod.yml restart"
echo "  应急直启 : 仅限临时排障，不作为生产常态路径"
echo "====================================="
