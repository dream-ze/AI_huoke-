# 运行形态说明

## 当前结论

当前项目不是单一的 Electron 桌面版，也不是单一的 Web 版，而是：

- Electron 桌面版
- Web 部署版
- 两者并行，共享同一套 FastAPI 后端能力与业务模型

## 依据

### Electron 桌面版

- `desktop/package.json` 中声明了 `electron/main.cjs` 作为入口。
- 打包脚本 `npm run dist` 会生成桌面安装包。
- `desktop/electron/main.cjs` 在打包模式下会拉起内置 `backend.exe`，并通过本地端口访问后端。

### Web 部署版

- `backend/main.py` 会在存在 `desktop/dist` 时直接托管前端静态资源。
- `backend/docker-compose.prod.yml` 会挂载服务器上的 `desktop/dist` 到后端容器。
- `deploy/docker-compose.yml` 提供了 Nginx 反向代理入口。

## 目标边界

为了减少后续混乱，推荐将项目定义为“共享领域后端的双前端交付形态”：

- 桌面端负责本地安装、配置、拉起本地后端。
- Web 版负责服务器部署、浏览器访问、Nginx 代理。
- 后端负责统一业务能力、统一数据库模型、统一 API 契约。

## 当前收口策略

- 后端入口统一由 `app.app_factory` 装配，避免 `main.py` 继续膨胀。
- Electron 与 Web 共用同一套 API 基础地址解析规则。
- 文档中明确“双形态并行，共享后端”，不再把项目描述成单一端形态。
