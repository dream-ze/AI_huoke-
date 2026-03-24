const DEFAULT_CONFIG = {
  apiBaseUrl: "http://127.0.0.1:8000",
  authToken: "",
  requestTimeoutMs: 12000,
  maxRetries: 2
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeBaseUrl(url) {
  if (!url) return DEFAULT_CONFIG.apiBaseUrl;
  return url.replace(/\/$/, "");
}

async function readConfig() {
  const data = await chrome.storage.sync.get("pluginConfig");
  return {
    ...DEFAULT_CONFIG,
    ...(data.pluginConfig || {}),
    apiBaseUrl: normalizeBaseUrl((data.pluginConfig || {}).apiBaseUrl || DEFAULT_CONFIG.apiBaseUrl)
  };
}

async function requestWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    });
  } finally {
    clearTimeout(timer);
  }
}

function isRetryableStatus(status) {
  return status === 429 || status >= 500;
}

async function postPluginCollect(payload) {
  const config = await readConfig();
  if (!config.authToken) {
    throw new Error("请先在插件中配置登录 Token");
  }

  const endpoint = `${config.apiBaseUrl}/api/v1/ai/plugin/collect`;
  const retries = Math.max(0, Number(config.maxRetries || 0));
  let lastError = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await requestWithTimeout(
        endpoint,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${config.authToken}`
          },
          body: JSON.stringify(payload)
        },
        Number(config.requestTimeoutMs || DEFAULT_CONFIG.requestTimeoutMs)
      );

      if (!response.ok) {
        const detail = await response.text();
        const trimmed = (detail || "").slice(0, 240);
        if (isRetryableStatus(response.status) && attempt < retries) {
          await sleep(400 * (attempt + 1));
          continue;
        }
        if (response.status === 401) {
          throw new Error("401 未授权，请更新 Token 后重试");
        }
        throw new Error(`请求失败(${response.status}): ${trimmed || "无返回详情"}`);
      }

      return await response.json();
    } catch (error) {
      lastError = error;
      if (attempt >= retries) break;
      await sleep(400 * (attempt + 1));
    }
  }

  throw lastError || new Error("采集请求失败");
}

async function testConnection() {
  const config = await readConfig();
  const endpoint = `${config.apiBaseUrl}/api/v1/health`;
  const response = await requestWithTimeout(
    endpoint,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json"
      }
    },
    Number(config.requestTimeoutMs || DEFAULT_CONFIG.requestTimeoutMs)
  );

  if (!response.ok) {
    throw new Error(`连接失败(${response.status})`);
  }

  return await response.json();
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || !message.type) {
    return false;
  }

  if (message.type === "PLUGIN_COLLECT_SUBMIT") {
    postPluginCollect(message.payload)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((error) => sendResponse({ ok: false, error: error.message || "采集失败" }));
    return true;
  }

  if (message.type === "PLUGIN_TEST_CONNECTION") {
    testConnection()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((error) => sendResponse({ ok: false, error: error.message || "连接失败" }));
    return true;
  }

  return false;
});
