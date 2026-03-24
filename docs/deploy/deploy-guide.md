# 部署指南

更新时间：2026-03-23

## 1. 适用范围

- 当前推荐：`backend/docker-compose.yml`
- 目标形态：`deploy/docker-compose.yml`

## 2. 发布前检查

- [ ] 代码已合并到发布分支
- [ ] 环境变量已按 `docs/deploy/env-example.md` 配置
- [ ] 数据库可连通，磁盘空间充足
- [ ] 本次迁移脚本已在预发验证

## 3. 部署步骤

1. 拉取最新代码并进入后端目录。
2. 执行数据库迁移（必须先于服务启动）：

```bash
cd backend
alembic upgrade head
```

3. 启动或更新服务：

```bash
docker compose -f docker-compose.yml up -d --build
```

4. 健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

5. 抽样验证关键链路：
- 登录接口
- `/api/v1/collect/intake` 入收件箱
- `/api/v1/ai/plugin/collect` 采集回传
- 发布任务 trace 与线索转客户

## 4. 回滚步骤

1. 记录当前版本信息（镜像 tag / commit hash）。
2. 停止当前版本容器：

```bash
docker compose -f docker-compose.yml down
```

3. 切换到上一个稳定版本代码或镜像 tag。
4. 启动旧版本：

```bash
docker compose -f docker-compose.yml up -d
```

5. 若本次迁移包含不可逆变更，必须先执行数据库回滚评估；可逆时执行：

```bash
cd backend
alembic downgrade -1
```

6. 回滚后执行健康检查与关键接口抽样。

## 5. 问题记录模板

发生发布异常时，请同步填写：
- `docs/operations/问题记录模板.md`

字段建议：
- 编号、时间、环境、现象、影响范围、临时止血、根因、修复方案、回归结论、责任人。
