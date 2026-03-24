# mobile-h5

移动采集入口（最小可运行版）。

## 已落地页面

- `index.html`：入口导航
- `src/pages/share-collect/index.html`：分享采集 -> `/api/v1/collect/intake`（`source_type=mobile_share`）
- `src/pages/screenshot-ocr/index.html`：截图 OCR -> `/api/v1/collect/ocr`
- `src/pages/quick-note/index.html`：快捷记录 -> `/api/v1/collect/intake`（`source_type=paste`）
- `src/pages/wecom-redirect/index.html`：企微转发承接 -> `/api/v1/collect/intake`（`source_type=wechat_forward`）

## 使用方式

当前为纯静态页面，无需构建。

在 `mobile-h5/` 目录执行：

```bash
python -m http.server 8081
```

访问：

- `http://127.0.0.1:8081/`

## 页面配置

每个页面都支持保存：

- API Base URL（默认 `http://127.0.0.1:8000`）
- Mobile Token（应急兜底，优先使用短期票据自动换取）
- 超时毫秒数
- 最大重试次数（0-3）

配置会保存在浏览器 `localStorage` 中。

## 鉴权收口

当前支持两种方式：

1. 推荐：通过后端短期票据换取 mobile-h5 Token
	- 先调用 `POST /api/auth/mobile-h5/ticket`
	- 可传 `redirect_path`，让后端直接返回带 `ticket` 的 H5 链接
	- 页面打开后会自动请求 `GET /api/auth/mobile-h5/exchange?ticket=...` 换取正式 Bearer Token
	- 换取成功后会自动清理地址栏中的敏感参数
2. 兜底：手动填写 Bearer Token

说明：当前仓库尚未接入企业微信真实 OAuth 换码与用户映射，所以本次先用短期签名票据完成移动端鉴权收口，后续可在有 corp/agent/userid 映射后替换成真实企微 OAuth。

## 弱网策略

- 所有 H5 页面统一支持超时控制与退避重试
- 401 会清空本地 token 并提示重新授权
- 429 / 5xx / 超时会按配置自动重试
- 表单提交增加前端重复提交保护
- `collect/intake` 与 `collect/ocr` 已支持 `client_request_id` 幂等承接，避免弱网重试导致重复入收件箱

## 待完善

- 接入企业微信真实 OAuth 换码与本地用户映射
- 上传链路增加压缩和断点续传
- 补齐移动端 UAT 记录（弱网、超时、重复提交）
