#!/bin/bash
# Docker 容器启动脚本 - 自动等待数据库、初始化表（测试用户默认关闭）
set -e

echo "===== 智获客 Backend Startup ====="

# ── 检查必要环境变量 ─────────────────────────────────────────────
echo "检查必要环境变量..."

# 必填配置检查
required_vars=("DATABASE_URL" "SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "错误: 环境变量 $var 未设置"
        exit 1
    fi
done

# SECRET_KEY安全检查
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "错误: SECRET_KEY长度不足32字符"
    exit 1
fi

if [ "$SECRET_KEY" = "change-me-to-a-real-secret-key-at-least-32-chars" ] || [ "$SECRET_KEY" = "your-secret-key-here" ]; then
    echo "错误: SECRET_KEY使用了默认占位值，请设置安全的密钥"
    exit 1
fi

echo "环境变量检查通过"

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
echo "执行数据库迁移..."
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "错误: 数据库迁移失败！请检查迁移文件和数据库连接。"
    exit 1
fi
echo "数据库迁移成功！"

# ── Redis连接检查（非强制，降级模式可运行）────────────────────────
if [ -n "$REDIS_URL" ]; then
    echo "检查Redis连接..."
    python3 -c "
import redis
import os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    r.ping()
    print('Redis连接正常')
except Exception as e:
    print(f'警告: Redis连接失败({e})，限流和缓存功能将降级')
" 2>/dev/null || echo "警告: Redis检查脚本执行失败，继续启动..."
fi

# ── 可选：创建测试用户（生产默认关闭）─────────────────────────────
if [ "${ENABLE_BOOTSTRAP_TEST_USER:-False}" = "True" ]; then
  echo "ENABLE_BOOTSTRAP_TEST_USER=True，开始创建测试用户..."
  python3 scripts/migrations/create_test_user.py 2>/dev/null || true
else
  echo "跳过测试用户初始化（ENABLE_BOOTSTRAP_TEST_USER=False）"
fi

# ── 启动 uvicorn ────────────────────────────────────────────────
echo "Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level ${LOG_LEVEL:-info}
