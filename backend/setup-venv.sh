#!/bin/bash
# ============================================================
# 智获客 - Python 虚拟环境部署方案（不用 Docker 跑后端）
# 适合: 已有 Python 3.10+ 的服务器
# 在服务器上执行: bash /opt/zhihuokeke/backend/setup-venv.sh
#
# 用 Docker 只跑 PostgreSQL + Ollama，后端用 venv 直接跑
# ============================================================
set -e

DEPLOY_DIR="/opt/zhihuokeke/backend"
VENV_DIR="$DEPLOY_DIR/.venv"

echo "====================================="
echo " 智获客 - Python 虚拟环境部署"
echo "====================================="

# ── 检查 Python ──────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[错误] Python3 未安装"
    echo "  apt-get install -y python3 python3-pip python3-venv"
    exit 1
fi
PY_VER=$(python3 --version)
echo "[OK] Python: $PY_VER"

cd "$DEPLOY_DIR"

# ── 启动 PostgreSQL 和 Ollama（Docker）──────────────────
echo ""
echo "[1/6] 启动 PostgreSQL + Ollama (Docker)..."

# 只启动 postgres 和 ollama 两个服务
docker compose up -d postgres ollama

echo "  等待 PostgreSQL..."
until docker exec zhihuokeke-db pg_isready -U postgres >/dev/null 2>&1; do
    sleep 2
done
echo "[OK] PostgreSQL 已就绪"

# ── 创建虚拟环境 ────────────────────────────────────────
echo ""
echo "[2/6] 创建 Python 虚拟环境..."
python3 -m venv "$VENV_DIR"
echo "[OK] venv 创建于: $VENV_DIR"

# ── 安装依赖 ────────────────────────────────────────────
echo ""
echo "[3/6] 安装 Python 依赖..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r requirements.txt -q
echo "[OK] 依赖安装完成"

# ── 配置 .env ────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo ""
    echo "[4/6] 创建 .env 配置..."
    cp .env.server .env
    # 修改 DATABASE_URL 为本地（postgres 在 Docker，映射到 localhost:5432）
    sed -i 's|DATABASE_URL=postgresql://postgres:Zhk_Db_2024@postgres:|DATABASE_URL=postgresql://postgres:Zhk_Db_2024@localhost:|' .env
    sed -i 's|DATABASE_HOST=postgres|DATABASE_HOST=localhost|' .env
    sed -i 's|OLLAMA_BASE_URL=http://ollama:11434|OLLAMA_BASE_URL=http://localhost:11434|' .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/CHANGE_ME_SECRET_KEY_MIN_32_CHARS/$SECRET/" .env
    echo "[OK] .env 已生成"
else
    echo "[4/6] .env 已存在，跳过"
fi

# ── 初始化数据库 ────────────────────────────────────────
echo ""
echo "[5/6] 初始化数据库表..."
"$VENV_DIR/bin/python" init_db.py
"$VENV_DIR/bin/python" create_test_user.py 2>/dev/null || true
echo "[OK] 数据库初始化完成"

# ── 安装 systemd 服务（可选）或直接后台启动 ─────────────
echo ""
echo "[6/6] 启动后端服务..."

# 写入 systemd service
if command -v systemctl &>/dev/null; then
    cat > /etc/systemd/system/zhihuokeke.service <<EOF
[Unit]
Description=智获客 Backend API
After=network.target

[Service]
Type=simple
WorkingDirectory=$DEPLOY_DIR
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable zhihuokeke
    systemctl restart zhihuokeke
    echo "[OK] systemd 服务已启动: systemctl status zhihuokeke"
else
    # 没有 systemd，用 nohup 后台运行
    nohup "$VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 --workers 2 \
        > /var/log/zhihuokeke.log 2>&1 &
    echo "[OK] 后台启动，PID=$!, 日志: /var/log/zhihuokeke.log"
fi

# ── 拉取 AI 模型 ────────────────────────────────────────
echo ""
echo "[INFO] 后台拉取 Ollama 模型 qwen2:1.5b..."
docker exec zhihuokeke-ollama ollama pull qwen2:1.5b &

echo ""
echo "====================================="
echo " 部署完成！(虚拟环境方案)"
echo "====================================="
echo ""
echo "  API 地址 : http://116.62.86.160:8000"
echo "  API 文档 : http://116.62.86.160:8000/docs"
echo "  测试账号 : 通过 TEST_USER_PASSWORD 显式指定（默认不建议固定密码）"
echo ""
echo "  venv 路径: $VENV_DIR"
echo "  查看日志: journalctl -u zhihuokeke -f  (systemd)"
echo "         或: tail -f /var/log/zhihuokeke.log (nohup)"
echo "====================================="
