const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const http = require("http");

const isDev = !app.isPackaged;

// ─── 配置文件路径 ────────────────────────────────────────────────
const CONFIG_PATH = path.join(app.getPath("userData"), "db-config.json");

// 默认 PostgreSQL 配置
const DEFAULT_CONFIG = {
  DATABASE_HOST: "localhost",
  DATABASE_PORT: "5432",
  DATABASE_USER: "postgres",
  DATABASE_PASSWORD: "password",
  DATABASE_NAME: "zhihuokeke",
  SECRET_KEY: "zhihuokeke-secret-key-change-me",
  BACKEND_PORT: "8000",
};

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")) };
    }
  } catch (e) {
    console.error("读取配置失败:", e.message);
  }
  return { ...DEFAULT_CONFIG };
}

function saveConfig(cfg) {
  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), "utf8");
}

// ─── 后端进程管理 ────────────────────────────────────────────────
let backendProcess = null;

function getBackendExePath() {
  if (isDev) return null; // dev 模式下假定后端已单独运行
  // 打包后 backend.exe 放在 resources/backend/ 目录
  return path.join(process.resourcesPath, "backend", "backend.exe");
}

function buildBackendEnv(cfg) {
  const dbUrl = `postgresql://${cfg.DATABASE_USER}:${cfg.DATABASE_PASSWORD}@${cfg.DATABASE_HOST}:${cfg.DATABASE_PORT}/${cfg.DATABASE_NAME}`;
  return {
    ...process.env,
    PORT: cfg.BACKEND_PORT || "8000",
    HOST: "127.0.0.1",
    DATABASE_URL: dbUrl,
    DATABASE_HOST: cfg.DATABASE_HOST,
    DATABASE_PORT: cfg.DATABASE_PORT,
    DATABASE_USER: cfg.DATABASE_USER,
    DATABASE_PASSWORD: cfg.DATABASE_PASSWORD,
    DATABASE_NAME: cfg.DATABASE_NAME,
    SECRET_KEY: cfg.SECRET_KEY,
    ACCESS_TOKEN_EXPIRE_MINUTES: "30",
  };
}

function startBackend(cfg) {
  const exePath = getBackendExePath();
  if (!exePath) {
    console.log("[后端] 开发模式，跳过启动后端进程");
    return;
  }
  if (!fs.existsSync(exePath)) {
    console.error("[后端] 找不到 backend.exe:", exePath);
    return;
  }

  console.log("[后端] 启动:", exePath);
  backendProcess = spawn(exePath, [], {
    env: buildBackendEnv(cfg),
    cwd: path.dirname(exePath),
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });

  backendProcess.stdout.on("data", (d) => console.log("[后端]", d.toString().trim()));
  backendProcess.stderr.on("data", (d) => console.error("[后端 err]", d.toString().trim()));
  backendProcess.on("exit", (code) => console.log("[后端] 进程退出，code:", code));
}

function stopBackend() {
  if (backendProcess) {
    try {
      backendProcess.kill("SIGTERM");
      setTimeout(() => {
        if (backendProcess && !backendProcess.killed) backendProcess.kill("SIGKILL");
      }, 3000);
    } catch (e) {
      console.error("[后端] 停止失败:", e.message);
    }
    backendProcess = null;
  }
}

// 轮询等待后端健康检查就绪
function waitForBackend(port, maxWait = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function check() {
      if (Date.now() - start > maxWait) return reject(new Error("后端启动超时"));
      const req = http.request({ hostname: "127.0.0.1", port, path: "/health", timeout: 1000 }, (res) => {
        if (res.statusCode === 200) return resolve();
        setTimeout(check, 1000);
      });
      req.on("error", () => setTimeout(check, 1000));
      req.end();
    }
    check();
  });
}

// ─── 窗口 ────────────────────────────────────────────────────────
let mainWin = null;

function createWindow(cfg) {
  mainWin = new BrowserWindow({
    width: 1400,
    height: 920,
    minWidth: 1120,
    minHeight: 760,
    title: "智获客",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWin.loadURL("http://localhost:5173");
    mainWin.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWin.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

// ─── IPC：配置读写 ────────────────────────────────────────────────
ipcMain.handle("get-db-config", () => loadConfig());
ipcMain.handle("save-db-config", async (_e, cfg) => {
  saveConfig(cfg);
  // 重启后端
  stopBackend();
  startBackend(cfg);
  const port = parseInt(cfg.BACKEND_PORT || "8000");
  try {
    await waitForBackend(port, 20000);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e.message };
  }
});
ipcMain.handle("check-backend", async () => {
  const cfg = loadConfig();
  const port = parseInt(cfg.BACKEND_PORT || "8000");
  try {
    await waitForBackend(port, 5000);
    return { running: true };
  } catch {
    return { running: false };
  }
});

// ─── 应用生命周期 ─────────────────────────────────────────────────
app.whenReady().then(async () => {
  const cfg = loadConfig();

  // 打包版本：启动后端进程
  startBackend(cfg);

  // 先创建窗口（会显示 Loading 界面）
  createWindow(cfg);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow(cfg);
  });
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopBackend();
});
