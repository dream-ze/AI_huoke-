# 兼容层退役清单

目的：避免兼容层无限期留存，保证迁移完成后及时清理。

## 1. 立项即定义退役时间

- 为每个兼容层记录 `owner`、`created_at`、`remove_after`。
- 推荐最长保留周期：2 个迭代。

## 2. 兼容层代码规范

- 兼容层只允许做转发，不允许新增业务逻辑。
- 文件头必须写明：
  - 兼容来源与目标（legacy -> new）
  - 计划删除日期
  - 负责人与追踪任务 ID

模板示例：

```python
"""
Compat Layer (temporary)
legacy: app.services.xxx
new: app.domains.xxx
remove_after: 2026-04-30
owner: backend-team
tracking: P0-compat-cleanup
"""
```

## 3. 统一弃用日志

- 在兼容层入口输出统一告警日志：`event=compat_layer_used`。
- 日志字段建议：`legacy_path`、`new_path`、`remove_after`、`owner`。
- 日志只打 warning，不打印敏感数据。

## 4. 迁移完成判定

- 代码层：仓库内无业务代码再 import 旧路径。
- 路由层：旧 URL 未注册到应用。
- 前端层：无旧路由映射或跳转。
- 测试层：新增路径的集成测试通过。

## 5. 删除动作

- 删除兼容文件。
- 删除旧导出（__init__ / barrel）。
- 删除兼容文档与临时注释。
- 在变更说明里记录清理批次。

## 6. 本仓库当前状态（2026-03-23）

- 已退役 API 兼容入口：`/api/collect/*`、`/api/ai/*`。
- 前端已退役旧页面路由：`/content`、`/ai`。
- 已清理前端兼容导出壳：`desktop/src/pages/ContentPage.tsx`、`desktop/src/pages/AIPage.tsx`、`desktop/src/pages/DashboardPage.tsx`。
