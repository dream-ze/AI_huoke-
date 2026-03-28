# PostgreSQL 远程部署与初始化清单

适用范围：
- 远程测试环境 / 正式环境
- Docker Compose 主路径
- 后端依赖 PostgreSQL + Redis + Ollama

## 1. 服务器准备

在服务器确认以下命令可用：

```bash
docker --version
docker compose version
python3 --version
curl --version
```

建议目录：

```bash
mkdir -p /opt/zhihuokeke/backend
mkdir -p /opt/zhihuokeke/desktop/dist
```

## 2. 远程 `.env` 与密钥配置

首次部署：

```bash
cd /opt/zhihuokeke/backend
cp .env.server .env
```

必须确认这些值不是占位值：

```env
DATABASE_PASSWORD=
DATABASE_URL=
SECRET_KEY=
```

建议最少检查项：
- `SECRET_KEY` 长度至少 32 位
- `DATABASE_URL` 指向 `postgres:5432/zhihuokeke`
- `USE_REDIS_RATE_LIMIT=True`
- `REDIS_URL=redis://redis:6379/0`
- `DEBUG=False`
- `CORS_ORIGINS` 已替换为真实域名或测试环境地址
- `ENABLE_BOOTSTRAP_TEST_USER=False`

## 3. PostgreSQL 初始化与迁移

当前主路径由容器启动脚本自动执行：
- 等待 PostgreSQL 就绪
- `alembic upgrade head`
- Alembic 不可用时回退 `python3 init_db.py`

部署后可手动确认：

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d zhihuokeke -c '\dt'
docker compose -f docker-compose.prod.yml logs --tail 200 backend
```

重点确认：
- `users`
- `source_contents`
- `normalized_contents`
- `material_items`
- `knowledge_documents`
- `knowledge_chunks`
- `generation_tasks`
- `publish_tasks`
- `leads`
- `customers`

## 4. 启动命令

```bash
cd /opt/zhihuokeke/backend
bash deploy.sh
```

或手动：

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

## 5. 部署后健康检查

必须检查：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/system/ops/health
curl http://127.0.0.1:8000/api/system/ops/readiness
```

期望：
- `database.ok=true`
- `redis.ok=true`
- `ollama.ok=true` 或至少错误信息明确
- `readiness` 返回 `200`

## 6. 日志与故障排查

查看全部容器日志：

```bash
docker compose -f docker-compose.prod.yml logs -f
```

按服务查看：

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f postgres
docker compose -f docker-compose.prod.yml logs -f redis
docker compose -f docker-compose.prod.yml logs -f ollama
```

当前容器已配置滚动日志：
- `max-size=10m`
- `max-file=5`

## 7. 发布前最小回归

至少执行以下链路：
1. 登录
2. 手动提交素材到收件箱
3. `v2 /materials/ingest-and-rewrite`
4. 发布任务创建 / 分配 / 提交
5. 线索生成 / 转客户

如果是正式发布，先完成页面验收清单：
- [post_deploy_uat_checklist.md](/D:/智获客/docs/operations/post_deploy_uat_checklist.md)

