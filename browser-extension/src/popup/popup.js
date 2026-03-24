const DEFAULT_CONFIG = {
  apiBaseUrl: "http://127.0.0.1:8000",
  authToken: "",
  requestTimeoutMs: 12000,
  maxRetries: 2
};

const apiBaseUrlEl = document.getElementById("apiBaseUrl");
const authTokenEl = document.getElementById("authToken");
const requestTimeoutMsEl = document.getElementById("requestTimeoutMs");
const maxRetriesEl = document.getElementById("maxRetries");
const statusEl = document.getElementById("status");

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.classList.remove("ok", "err");
  if (type === "ok") statusEl.classList.add("ok");
  if (type === "err") statusEl.classList.add("err");
}

function normalizeBaseUrl(url) {
  return (url || DEFAULT_CONFIG.apiBaseUrl).trim().replace(/\/$/, "");
}

async function loadConfig() {
  const data = await chrome.storage.sync.get("pluginConfig");
  const config = {
    ...DEFAULT_CONFIG,
    ...(data.pluginConfig || {})
  };

  apiBaseUrlEl.value = normalizeBaseUrl(config.apiBaseUrl);
  authTokenEl.value = config.authToken || "";
  requestTimeoutMsEl.value = Number(config.requestTimeoutMs || DEFAULT_CONFIG.requestTimeoutMs);
  maxRetriesEl.value = Number(config.maxRetries || DEFAULT_CONFIG.maxRetries);
}

async function saveConfig() {
  const payload = {
    apiBaseUrl: normalizeBaseUrl(apiBaseUrlEl.value),
    authToken: (authTokenEl.value || "").trim(),
    requestTimeoutMs: Number(requestTimeoutMsEl.value || DEFAULT_CONFIG.requestTimeoutMs),
    maxRetries: Number(maxRetriesEl.value || DEFAULT_CONFIG.maxRetries)
  };

  await chrome.storage.sync.set({ pluginConfig: payload });
  setStatus("配置已保存", "ok");
}

async function getActiveTabId() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs || !tabs[0] || typeof tabs[0].id !== "number") {
    throw new Error("未找到当前标签页");
  }
  return tabs[0].id;
}

async function sendMessageToTab(tabId, message) {
  return await chrome.tabs.sendMessage(tabId, message);
}

async function sendMessageToBackground(message) {
  return await chrome.runtime.sendMessage(message);
}

async function testConnection() {
  setStatus("正在测试连接...", "");
  const res = await sendMessageToBackground({ type: "PLUGIN_TEST_CONNECTION" });
  if (!res || !res.ok) {
    throw new Error((res && res.error) || "连接失败");
  }
  setStatus("连接成功：后端健康检查通过", "ok");
}

async function collectCurrentTab() {
  setStatus("正在采集页面...", "");
  const tabId = await getActiveTabId();
  const collectRes = await sendMessageToTab(tabId, { type: "PLUGIN_COLLECT_FROM_PAGE" });

  if (!collectRes || !collectRes.ok) {
    throw new Error((collectRes && collectRes.error) || "页面采集失败");
  }

  const submitRes = await sendMessageToBackground({
    type: "PLUGIN_COLLECT_SUBMIT",
    payload: collectRes.payload
  });

  if (!submitRes || !submitRes.ok) {
    throw new Error((submitRes && submitRes.error) || "上报后端失败");
  }

  const data = submitRes.data || {};
  setStatus(
    "采集成功\n" +
      "plugin_collection_id: " + data.id + "\n" +
      "content_asset_id: " + (data.synced_content_asset_id || "-") + "\n" +
      "insight_item_id: " + (data.synced_insight_item_id || "-"),
    "ok"
  );
}

document.getElementById("saveBtn").addEventListener("click", () => {
  saveConfig().catch((error) => setStatus(error.message || "保存失败", "err"));
});

document.getElementById("testBtn").addEventListener("click", () => {
  testConnection().catch((error) => setStatus(error.message || "连接失败", "err"));
});

document.getElementById("collectBtn").addEventListener("click", () => {
  collectCurrentTab().catch((error) => setStatus(error.message || "采集失败", "err"));
});

document.getElementById("clearBtn").addEventListener("click", async () => {
  authTokenEl.value = "";
  await saveConfig();
  setStatus("Token 已清空", "ok");
});

loadConfig().catch((error) => setStatus(error.message || "初始化失败", "err"));
