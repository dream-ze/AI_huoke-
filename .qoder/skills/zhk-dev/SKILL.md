---
name: zhk-dev
description: 智获客项目开发流程，适用于新功能开发、修改现有功能
---

# 智获客开发流程

## 触发条件
- 用户要求添加新功能
- 用户要求修改现有功能
- 涉及多个文件的改动

## 执行步骤

### 1. 需求澄清（30秒）
快速确认：
- [ ] 改什么？（具体功能点）
- [ ] 影响哪些模块？（采集/AI/客户/发布）
- [ ] 有无现有代码可参考？

### 2. 定位相关代码
按模块快速定位：
```
backend/app/
├── api/v1/          # API路由
├── services/        # 业务逻辑（核心）
├── schemas/         # 请求/响应模型
├── models/          # 数据库模型
└── ai/              # AI相关服务
```

### 3. 实现顺序
1. **Schema** → 定义请求/响应结构
2. **Service** → 实现业务逻辑
3. **API** → 注册路由
4. **前端** → 调用接口（如需要）

### 4. 验证清单
- [ ] 接口能正常调用（curl或Swagger）
- [ ] 关键路径无报错
- [ ] 数据库操作正确

## 常见模块位置

| 功能 | 后端位置 | 前端位置 |
|------|----------|----------|
| 内容采集 | `services/collect_*.py` | `pages/collect/` |
| AI改写 | `ai/rewrite/`, `services/rewrite_*.py` | `pages/workbench/` |
| 素材库 | `services/material_*.py` | `pages/material/` |
| 知识库 | `services/knowledge_*.py` | `pages/knowledge/` |
| 客户管理 | `services/customer_*.py` | `pages/customer/` |

## 注意事项
1. **API版本**：新接口放 `/api/v1/`，兼容旧接口时加 `deprecated` 标记
2. **环境变量**：AI相关配置在 `.env` 中，前缀 `ARK_` 或 `OLLAMA_`
3. **数据库迁移**：改表结构需执行 `alembic revision --autogenerate`
