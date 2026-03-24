#!/bin/bash
# Docker 容器启动脚本 - 自动等待数据库、初始化表（测试用户默认关闭）
set -e

echo "===== 智获客 Backend Startup ====="

# ── 等待 PostgreSQL 就绪 ──────────────────────────────────────────
echo "Waiting for PostgreSQL..."
until python3 - <<'PY' 2>/dev/null
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ["DATABASE_URL"])
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
do
  echo "  PostgreSQL not ready, retry in 2s..."
  sleep 2
done
echo "PostgreSQL is ready!"

# ── 初始化数据库表（幂等）────────────────────────────────────────
echo "Running Alembic migrations..."
if python3 -c "import alembic" 2>/dev/null; then
  if alembic upgrade head; then
    echo "Alembic migrations applied!"
  else
    echo "[WARN] Alembic migrations failed, falling back to create_all..."
    python3 init_db.py
  fi
else
  echo "[WARN] Alembic not installed, falling back to create_all..."
  python3 init_db.py
fi

# ── 可选：创建测试用户（生产默认关闭）─────────────────────────────
if [ "${ENABLE_BOOTSTRAP_TEST_USER:-False}" = "True" ]; then
  echo "ENABLE_BOOTSTRAP_TEST_USER=True，开始创建测试用户..."
  python3 create_test_user.py 2>/dev/null || true
else
  echo "跳过测试用户初始化（ENABLE_BOOTSTRAP_TEST_USER=False）"
fi

# ── 启动 uvicorn ────────────────────────────────────────────────
echo "Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
