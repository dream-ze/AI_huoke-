# 智获客浏览器插件（Chrome / Edge）

用于在内容平台页面采集结构化内容，并回传到后端接口：
- `/api/v1/ai/plugin/collect`

当前版本已实现：
- Manifest v3（Chrome/Edge 通用）
- Content Script 页面提取
- Background 上报与重试（401/429/5xx/超时可感知）
- Popup 配置（API Base URL、Token、超时、重试）

## 目录说明

- `manifest.json`：插件清单
- `src/content/content-script.js`：页面数据提取
- `src/background/background.js`：后端通信与重试
- `src/popup/popup.html` + `src/popup/popup.js`：操作面板
- `src/parsers/platform-parser.js`：平台识别工具（预留复用）
- `src/api/client.js`：API 客户端基础工具（预留复用）

## 安装步骤（Chrome / Edge）

1. 打开浏览器扩展管理页，开启开发者模式。
2. 选择“加载已解压的扩展程序”。
3. 选择 `browser-extension` 目录（包含 `manifest.json`）。
4. 安装后点击插件图标，进入弹窗。

## 首次配置

在插件弹窗填入并保存：
- `API Base URL`：例如 `http://127.0.0.1:8000`
- `Bearer Token`：后端登录态 token
- `超时(ms)`：默认 `12000`
- `重试次数`：默认 `2`

建议先点击“测试连接”，确保 `/api/v1/health` 可访问。

## 采集与回传链路

1. 打开目标页面（http/https）。
2. 点击“采集当前页”。
3. 插件执行流程：
	- Content Script 提取 `title/content/author/url/tags/comments_json`
	- Background 调用 `/api/v1/ai/plugin/collect`
	- 成功后回显 `plugin_collection_id`、`synced_content_asset_id`、`synced_insight_item_id`

## 回归清单

请按文档逐项验收：
- `docs/operations/浏览器插件联调与回归清单_2026-03-23.md`

## 常见问题

- 401 未授权：更新弹窗中的 Token 后重试。
- 429/5xx：插件会按配置自动重试，仍失败会提示错误码。
- 网络超时：提高超时阈值或检查后端地址。
- 页面采集为空：部分平台动态渲染受限，请人工补录后再入库。
