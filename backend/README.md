# 智获客后端

FastAPI + PostgreSQL 后端系统

## 快速开始

### 1. 环境配置

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，设置你的配置
```

### 2. Docker 方式运行

```bash
# 启动所有服务（PostgreSQL + Backend + Ollama + Redis）
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

### 3. 本地运行

```bash
# 安装依赖
pip install poetry
poetry install

# 启动 PostgreSQL（确保已安装）
# 或使用 Docker 只启动数据库
docker-compose up -d postgres

# 设置 .env 文件
cp .env.example .env

# 运行迁移（如有）
# alembic upgrade head

# 启动应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 数据库迁移（Alembic）

已补齐最小 Alembic 骨架：
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/*.py`

在 `backend/` 目录执行：

```bash
# 查看当前版本
alembic current

# 升级到最新版本
alembic upgrade head

# 回滚 1 个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade 20260323_01

# 查看迁移历史
alembic history --verbose
```

说明：
- Alembic 优先使用环境变量 `DATABASE_URL`。
- 若未配置，则回退到 `alembic.ini` 里的 `sqlalchemy.url`。

## API 文档

服务运行后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

火山方舟接入示例文档：
- `火山方舟_Responses_API_调用指南.md`

## 项目结构

```
backend/
├── app/
│   ├── models/          # SQLAlchemy ORM 模型
│   ├── schemas/         # Pydantic 数据模型
│   ├── services/        # 业务逻辑服务
│   ├── api/
│   │   └── endpoints/   # API 路由
│   └── core/
│       ├── config.py    # 配置
│       ├── database.py  # 数据库连接
│       └── security.py  # 认证和加密
├── main.py              # FastAPI 应用入口
├── pyproject.toml       # Poetry 项目配置
└── docker-compose.yml   # Docker 编排
```

## 核心功能

- **用户认证**: JWT Token 认证
- **内容管理**: 创建、编辑、删除内容素材
- **AI 改写**: 多平台内容改写（小红书、抖音、知乎等）
- **合规检查**: 自动检测风险表达
- **客户管理**: 客户信息和跟进记录
- **数据看板**: 发布效果分析和转化数据
- **浏览器插件**: 支持插件采集内容

## API 端点概览

### 认证 (/api/auth)
- POST `/register` - 注册用户
- POST `/login` - 登录
- GET `/me` - 获取当前用户

### 内容 (/api/content)
- POST `/create` - 创建内容
- GET `/list` - 内容列表
- GET `/{content_id}` - 获取内容详情
- PUT `/{content_id}` - 更新内容
- DELETE `/{content_id}` - 删除内容

### 合规 (/api/compliance)
- POST `/check` - 合规检查

### 客户 (/api/customer)
- POST `/create` - 创建客户
- GET `/list` - 客户列表
- POST `/{customer_id}/follow` - 添加跟进记录

### 发布 (/api/publish)
- POST `/create` - 创建发布记录
- GET `/list` - 发布记录列表
- PUT `/{record_id}` - 更新发布数据

### 仪表板 (/api/dashboard)
- GET `/summary` - 今日概览
- GET `/trend` - 趋势数据
- GET `/platform` - 平台分析
- GET `/topics` - 主题排行
- GET `/ai-call-stats` - AI 调用统计（按日、按用户聚合）

### AI (/api/ai)
- POST `/rewrite/xiaohongshu` - 小红书改写
- POST `/rewrite/douyin` - 抖音改写
- POST `/rewrite/zhihu` - 知乎改写
- POST `/ark/vision` - 火山引擎图片理解（Ark Responses）
- POST `/plugin/collect` - 插件采集

### AI 可观测性与限流
- Ark 调用会记录日志到 `ark_call_logs`，包含成功/失败、耗时、token 用量、用户 ID。
- `/api/ai/ark/vision` 已升级为 Redis 分布式限流（Redis 不可用时自动降级到进程内限流）。

## 技术栈

- FastAPI: Web 框架
- SQLAlchemy: ORM
- PostgreSQL: 数据库
- Pydantic: 数据验证
- Ollama: 本地 LLM
- Volcano Engine: 云端大模型（可选）

## 开发

```bash
# 代码格式化
black .
isort .

# 代码检查
flake8 .

# 类型检查
mypy .

# 单元测试
pytest

# 必跑回归（注册序列漂移自愈 + 唯一约束 400）
pytest -q test_main.py -k "sequence_drift or unique_constraint"

# PostgreSQL 集成回归（需可用的 PostgreSQL）
set RUN_POSTGRES_REGRESSION=1
set TEST_POSTGRES_DATABASE_URL=postgresql://postgres:password@localhost/zhihuokeke
pytest -q -m "postgres_regression" test_user_service_postgres_regression.py
```

## 生产部署

1. 统一主路径：使用 `docker compose -f docker-compose.prod.yml up -d --build`
2. 仅在故障排查时临时使用 Python 直启，恢复后回到 Docker 主路径
3. 修改 `.env` 中的敏感信息
4. 使用强密钥代替 SECRET_KEY
5. 设置 DEBUG=False
6. 配置 HTTPS
7. 设置适当的 CORS 源

## 常见问题

### 如何修改数据库连接？
编辑 `.env` 文件中的 `DATABASE_URL`

### 如何使用云端大模型？
设置 `USE_CLOUD_MODEL=True`、`ARK_API_KEY`，并按需设置 `ARK_BASE_URL`、`ARK_MODEL`

### 如何启用 Redis 分布式限流？
设置 `USE_REDIS_RATE_LIMIT=True`，并配置 `REDIS_URL`（如 Docker 环境可用 `redis://redis:6379/0`）

### 如何添加新的数据库模型？
1. 在 `app/models/models.py` 中定义模型
2. 在 `app/schemas/schemas.py` 中定义 schema
3. 创建迁移脚本
4. 在相应的 service 中添加业务逻辑
5. 在 API 端点中暴露接口

## 许可证

MIT
