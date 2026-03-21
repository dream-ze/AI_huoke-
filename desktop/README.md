# 智获客桌面端

React + Electron 桌面客户端。

## 运行

1. 安装依赖
npm install

2. 仅启动网页端（推荐当前阶段）
npm run dev:web

默认网页地址：
- http://localhost:5173

局域网访问地址（其他电脑可打开）：
- http://本机IP:5173

推荐命令（显式 LAN 模式）：
- npm run dev:web:lan

3. 启动桌面开发模式（网页 + Electron）
npm run dev

默认会启动：
- Vite 前端: http://localhost:5173
- Electron 桌面窗口

## 打包 Windows 安装包

npm run dist

输出目录:
- release/

## 环境变量

复制 .env.example 为 .env 并按需修改:

VITE_API_BASE_URL=http://localhost:8000

## 与后端配合

请先启动后端服务再登录桌面端。

## 其他电脑访问（网页端）

1. 在后端机器启动 API（默认 8000 端口，监听 0.0.0.0）。
2. 在前端机器启动网页：`npm run dev:web:lan`。
3. 确保系统防火墙放行 TCP 端口：`5173`（前端）和 `8000`（后端）。
4. 其他电脑通过 `http://前端机器IP:5173` 打开页面。

说明：前端已内置 API 回退逻辑，会自动把 API 指向当前访问主机的 `:8000`。如后端不在同一台机器，请设置 `VITE_API_BASE_URL` 为后端机器地址。
