# 目录重构执行方案（2026-03-23）

## 目标

将当前仓库从“后端单体+桌面端页面平铺”迁移到多端协同的统一工程结构，并保证主链路不中断。

## 已完成（第一阶段）

- 统一后端路由注册入口：`backend/app/api/router.py`
- 后端入口切换为注册函数：`backend/main.py`
- 增加 `DB_AUTO_CREATE_TABLES` 配置，避免迁移链被入口强绑定
- 建立目标目录骨架：`docs/`、`deploy/`、`mobile-h5/`、`browser-extension/`、`shared/`、`sql/`
- 建立后端新落点：`api/v1`、`repositories`、`ai`、`rules`、`tasks`、`integrations/volcengine`

## 下一步（第二阶段）

1. API 迁移：将 `backend/app/api/endpoints` 分批迁入 `backend/app/api/v1`。
2. 服务迁移：将 `backend/app/services` 按领域迁入 `backend/app/domains/*`。
3. 前端迁移：将 `desktop/src/pages/*.tsx` 逐步拆到 `desktop/src/pages/<domain>/`。
4. 部署迁移：把 `backend/docker-compose.yml` 的生产要素分拆到 `deploy/`。

## 我的建议

1. 目录先行，但不要一次性全量移动代码。
2. 每次只迁一个领域，迁完立刻补回归测试。
3. 先打通链路再优化命名：采集 -> 收件箱 -> 素材 -> AI -> 审核 -> 发布 -> 线索。
4. 迁移期间保留兼容层，避免前端和脚本同时断裂。
5. 文档以 `docs/` 为唯一主入口，历史说明文件逐步归档。
