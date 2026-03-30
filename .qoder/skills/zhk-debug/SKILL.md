---
name: zhk-debug
description: 智获客项目调试指南，用于排查错误和问题
---

# 智获客调试指南

## 触发条件
- 接口报错
- 功能不工作
- 数据异常

## 快速诊断流程

### 1. 确定问题类型（10秒）
```
前端报错 → 检查网络请求 → 看后端日志
后端报错 → 看堆栈信息 → 定位具体函数
数据异常 → 查数据库 → 追溯写入点
```

### 2. 常见问题速查

| 症状 | 原因 | 解决 |
|------|------|------|
| 按钮无响应 | 接口不存在/参数不对 | 检查路由注册、参数名 |
| 500错误 | 服务层异常 | 看uvicorn日志 |
| 422错误 | 请求参数校验失败 | 检查Schema定义 |
| 401/403 | 认证/权限问题 | 检查token |
| AI返回空 | 模型配置/prompt问题 | 检查.env中ARK_*配置 |
| 数据没入库 | Pipeline断裂 | 检查事务提交 |

### 3. 日志查看
```bash
# 后端日志
tail -f backend/logs/app.log

# 数据库查询
psql -h localhost -U postgres -d zhihuokeke
```

### 4. 已知坑点

**采集Pipeline**：
- 自动入库需提取结构化字段（topic/hook_sentence/cta_style）
- 跳过收件箱直接写mvp_knowledge_items

**前后端联调**：
- status字段前后端命名需一致
- keyword字段注意大小写

**AI服务**：
- Ollama需在localhost:11434运行
- 火山方舟需配置ARK_API_KEY和ARK_EMBEDDING_MODEL

## 调试步骤
1. 复现问题
2. 读日志/错误信息
3. 定位到具体函数
4. 单点验证（print/断点）
5. 修复并验证
