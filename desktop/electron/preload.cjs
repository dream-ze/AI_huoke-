const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  version: "0.1.0",
  isElectron: true,
  // 数据库配置
  getDbConfig: () => ipcRenderer.invoke("get-db-config"),
  saveDbConfig: (cfg) => ipcRenderer.invoke("save-db-config", cfg),
  checkBackend: () => ipcRenderer.invoke("check-backend"),
});
