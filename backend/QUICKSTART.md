# 智获客 - 完整开发指南

## 📋 项目概述

**智获客**是一个AI驱动的内容获客运营系统，integrates：
- 内容采集（手动+浏览器插件）
- AI内容改写（多平台）
- 合规审核检查
- 微信客户管理
- 数据分析看板

## 🚀 快速启动

### 方案 A：Docker 一键启动（推荐）
```bash
cd backend
docker-compose up -d
```

访问：
- API: http://localhost:8000
- 文档: http://localhost:8000/docs
- 数据库: localhost:5432
- Ollama: http://localhost:11434

### 方案 B：本地开发
```bash
# 1. 安装依赖
cd backend
pip install poetry
poetry install

# 2. 启动 PostgreSQL（Docker）
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=zhihuokeke \
  -p 5432:5432 \
  postgres:15

# 3. 初始化数据库
python init_db.py

# 3.1（推荐）执行数据库迁移
alembic upgrade head

# 4. 创建测试用户
python create_test_user.py

# 5. 启动应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 数据库迁移常用命令

在 `backend/` 目录执行：

```bash
# 查看当前版本
alembic current

# 升级到最新
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看历史
alembic history --verbose
```

## 📁 项目结构

```
backend/
├── app/
│   ├── models/          # 数据库模型
│   │   └── models.py    # ORM模型定义
│   ├── schemas/         # API 数据模型
│   ├── services/        # 业务逻辑层
│   │   ├── user_service.py        # 用户管理
│   │   ├── content_service.py     # 内容管理
│   │   ├── ai_service.py          # AI改写
│   │   ├── compliance_service.py  # 合规检查
│   │   ├── customer_service.py    # 客户管理
│   │   └── dashboard_service.py   # 数据分析
│   ├── api/
│   │   └── endpoints/   # API 路由
│   │       ├── auth.py
│   │       ├── content.py
│   │       ├── compliance.py
│   │       ├── customer.py
│   │       ├── publish.py
│   │       ├── dashboard.py
│   │       └── ai.py
│   └── core/
│       ├── config.py    # 配置管理
│       ├── database.py  # 数据库连接
│       └── security.py  # JWT认证
├── main.py              # FastAPI 入口
├── init_db.py           # 数据库初始化
├── create_test_user.py  # 创建测试用户
├── test_api.py          # API 测试脚本
│
└── docker-compose.yml   # Docker 编排
```

## 🔌 API 端点速查

### 认证
```
POST   /api/auth/register    - 注册用户
POST   /api/auth/login       - 登录
GET    /api/auth/me          - 获取当前用户
```

### 内容管理
```
POST   /api/content/create   - 创建内容
GET    /api/content/list     - 内容列表
GET    /api/content/{id}     - 获取具体内容
PUT    /api/content/{id}     - 更新内容
DELETE /api/content/{id}     - 删除内容
GET    /api/content/search/topic - 按主题搜索
```

### 合规审核
```
POST   /api/compliance/check - 合规检查
```

### 客户管理
```
POST   /api/customer/create  - 创建客户
GET    /api/customer/list    - 客户列表
GET    /api/customer/{id}    - 获取客户
PUT    /api/customer/{id}    - 更新客户
POST   /api/customer/{id}/follow - 添加跟进
DELETE /api/customer/{id}    - 删除客户
GET    /api/customer/pending/list - 待跟进列表
```

### 发布记录
```
POST   /api/publish/create   - 创建发布记录
GET    /api/publish/list     - 发布列表
PUT    /api/publish/{id}     - 更新发布数据
```

### 数据看板
```
GET    /api/dashboard/summary           - 今日概览
GET    /api/dashboard/trend             - 趋势数据
GET    /api/dashboard/platform          - 平台分析
GET    /api/dashboard/topics            - 主题排行
GET    /api/dashboard/high-quality-content - 高质量内容
```

### AI改写
```
POST   /api/ai/rewrite/xiaohongshu - 小红书改写
POST   /api/ai/rewrite/douyin      - 抖音改写
POST   /api/ai/rewrite/zhihu       - 知乎改写
POST   /api/ai/plugin/collect      - 插件采集
```

## 🧪 测试 API

### 使用测试脚本
```bash
python test_api.py
```

### 使用 Swagger UI
访问 http://localhost:8000/docs 进行交互式测试

### 使用 curl 示例
```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"YOUR_STRONG_PASSWORD"}'

# 创建内容
curl -X POST http://localhost:8000/api/content/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform":"xiaohongshu",
    "content_type":"post",
    "title":"Test",
    "content":"Test content"
  }'
```

## 🛠 开发指南

### 添加新的 API 端点

1. **定义 schema** (app/schemas/schemas.py)
```python
class MyDataCreate(BaseModel):
    field1: str
    field2: int
```

2. **创建 service** (app/services/my_service.py)
```python
class MyService:
    @staticmethod
    def create_item(db, data):
        # 业务逻辑
        pass
```

3. **创建 API 路由** (app/api/endpoints/my_endpoint.py)
```python
@router.post("/create")
def create_item(data: MyDataCreate, current_user: dict = Depends(verify_token)):
    # 调用 service
    return MyService.create_item(db, data)
```

4. **注册路由** (main.py)
```python
from app.api.endpoints import my_router
app.include_router(my_router)
```

### 修改数据库模型

1. 在 `app/models/models.py` 中添加新表
2. 重新初始化数据库或使用迁移工具
3. 创建对应的 schema
4. 在 service 中实现逻辑
5. 创建 API 端点

### 环境变量配置

复制 `.env.example` 为 `.env`：
```bash
cp .env.example .env
```

关键配置：
```
DATABASE_URL=postgresql://user:password@host/dbname
SECRET_KEY=YOUR_RANDOM_SECRET_KEY_AT_LEAST_32_CHARS
OLLAMA_BASE_URL=http://localhost:11434
USE_CLOUD_MODEL=False
```

## 🔑 认证说明

所有需要认证的 API 都需要在请求头中添加：
```
Authorization: Bearer {access_token}
```

获取 token 方式：
1. 注册用户
2. 调用 login 端点获得 `access_token`
3. 在后续请求中使用这个 token

## 📊 数据库图

```
users (1) ──────────────── (n) content_assets
  │                              │
  │                              ├─→ rewritten_contents
  │                              └─→ plugin_collections
  │
  ├─ customers
  │
  └─ (n 关系到) publish_records ←── rewritten_contents
```

## 🚢 生产部署

生产环境统一主路径：Docker Compose（`docker-compose.prod.yml`）。
Python 直启仅作为临时应急排障方案，故障恢复后应回切到 Docker。

### 环境变量设置
```bash
# .env (生产)
DEBUG=False
SECRET_KEY=use-a-strong-random-key
DATABASE_URL=postgresql://prod_user:strong_password@prod_server/prod_db
CORS_ORIGINS=["https://yourdomain.com"]
USE_CLOUD_MODEL=True
ARK_API_KEY=your-cloud-api-key
```

### Docker 部署
```bash
# 推荐：统一生产主路径
docker compose -f docker-compose.prod.yml up -d --build

# 查看日志
docker compose -f docker-compose.prod.yml logs -f backend
```

### 使用 Nginx 反向代理
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📝 常见任务

### 重置数据库
```bash
python init_db.py drop
python init_db.py init
```

### 查看数据库
```bash
# 进入 PostgreSQL
psql -U postgres -d zhihuokeke

# 查看表
\dt

# 查询数据
SELECT * FROM users;
```

### 调试
启用 DEBUG 模式：
```bash
# .env
DEBUG=True

# 启动应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🐛 常见问题

**Q: 数据库连接失败?**
A: 检查 DATABASE_URL 和 PostgreSQL 是否运行

**Q: Token 过期?**
A: 重新登录获取新 token

**Q: CORS 错误?**
A: 在 .env 中配置正确的 CORS_ORIGINS

## 📚 技术文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Pydantic 文档](https://docs.pydantic.dev/)

## 📞 下一步

1. **创建前端** (React + Electron)
   - 集成这些 API
   - 构建 UI 界面

2. **创建浏览器插件**
   - 实现内容采集
   - 调用 `/api/ai/plugin/collect`

3. **集成大模型**
   - 配置 Ollama 本地模型
   - 后期切换到火山引擎

4. **部署上线**
   - 云服务器部署
   - 配置域名和 HTTPS
