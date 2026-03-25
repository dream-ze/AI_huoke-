#!/bin/bash
# ============================================================
# browser_collector 一键部署脚本（在服务器上执行）
# 服务器：116.62.86.160   部署目录：/www/browser_collector
# ============================================================
set -e

DEPLOY_DIR="/www/browser_collector"
VENV="$DEPLOY_DIR/venv"

echo "====== [1/6] 安装系统依赖 ======"
apt-get update -y
apt-get install -y --no-install-recommends \
    python3-venv python3-full \
    libnss3 libnspr4 libdbus-1-3 \
    libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
    libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2t64 \
    fonts-noto-cjk wget curl

echo "====== [2/6] 创建虚拟环境并安装 Python 依赖 ======"
cd "$DEPLOY_DIR"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r requirements.txt

echo "====== [3/6] 安装 Playwright 浏览器内核 ======"
"$VENV/bin/python" -m playwright install chromium
"$VENV/bin/python" -m playwright install-deps chromium

echo "====== [4/6] 写入生产环境变量 ======"
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env.prod" "$DEPLOY_DIR/.env"
    echo "已从 .env.prod 复制为 .env"
else
    echo ".env 已存在，跳过覆盖"
fi

echo "====== [5/6] 部署 systemd 服务 ======"
cat > /etc/systemd/system/browser_collector.service << EOF
[Unit]
Description=Browser Collector Service (Playwright)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR
Environment="PYTHONPATH=$DEPLOY_DIR"
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 1
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable browser_collector
systemctl restart browser_collector
sleep 3

echo "====== [6/6] 健康检查 ======"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8005/health)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 部署成功！服务正常运行在 127.0.0.1:8005"
    curl -s http://127.0.0.1:8005/health
else
    echo "❌ 健康检查失败（HTTP $HTTP_CODE），查看日志："
    journalctl -u browser_collector -n 30 --no-pager
    exit 1
fi
