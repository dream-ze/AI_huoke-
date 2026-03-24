const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 12000;
const DEFAULT_MAX_RETRIES = 2;
const SENSITIVE_QUERY_KEYS = ["token", "access_token", "ticket", "auth_ticket", "mobile_ticket"];
const pendingRequestKeys = new Set();

function toSafePositiveNumber(value, fallback) {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? num : fallback;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readQueryValue(params, keys) {
  for (const key of keys) {
    const value = params.get(key);
    if (value) return value;
  }
  return "";
}

function cleanupSensitiveQuery() {
  const url = new URL(window.location.href);
  let changed = false;
  SENSITIVE_QUERY_KEYS.forEach((key) => {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  });

  if (changed) {
    const target = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState({}, document.title, target);
  }
}

function requestWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  return fetch(url, {
    ...options,
    signal: controller.signal,
  }).finally(() => {
    window.clearTimeout(timer);
  });
}

function isRetryableStatus(status) {
  return status === 408 || status === 429 || status >= 500;
}

function formatErrorMessage(status, data) {
  if (typeof data === "string") return `HTTP ${status}: ${data}`;
  if (data && typeof data === "object" && data.detail) return `HTTP ${status}: ${data.detail}`;
  return `HTTP ${status}: ${JSON.stringify(data)}`;
}

export function loadRuntimeConfig() {
  return {
    baseUrl: localStorage.getItem("zhk_h5_api_base_url") || DEFAULT_BASE_URL,
    token: localStorage.getItem("zhk_h5_token") || "",
    requestTimeoutMs: toSafePositiveNumber(localStorage.getItem("zhk_h5_timeout_ms"), DEFAULT_TIMEOUT_MS),
    maxRetries: Math.max(0, Math.min(3, Number(localStorage.getItem("zhk_h5_max_retries") || DEFAULT_MAX_RETRIES))),
  };
}

export function saveRuntimeConfig(baseUrl, token, extras = {}) {
  localStorage.setItem("zhk_h5_api_base_url", (baseUrl || "").trim() || DEFAULT_BASE_URL);
  localStorage.setItem("zhk_h5_token", (token || "").trim());
  localStorage.setItem(
    "zhk_h5_timeout_ms",
    String(toSafePositiveNumber(extras.requestTimeoutMs, DEFAULT_TIMEOUT_MS)),
  );
  localStorage.setItem(
    "zhk_h5_max_retries",
    String(Math.max(0, Math.min(3, Number(extras.maxRetries ?? DEFAULT_MAX_RETRIES)))),
  );
}

export async function bootstrapPageAuth(root) {
  const config = loadRuntimeConfig();
  const query = new URLSearchParams(window.location.search);
  const baseUrlFromQuery = readQueryValue(query, ["api_base_url", "baseUrl"]);
  const tokenFromQuery = readQueryValue(query, ["token", "access_token"]);
  const code = query.get("code") || "";
  const ticket = readQueryValue(query, ["ticket", "auth_ticket", "mobile_ticket"]);

  if (baseUrlFromQuery) {
    config.baseUrl = baseUrlFromQuery.trim();
  }
  if (tokenFromQuery) {
    config.token = tokenFromQuery.trim();
  }

  const base = config.baseUrl.replace(/\/$/, "");

  // ── 优先：企业微信 OAuth code 换码 ──────────────────────────────────────
  if (code) {
    setAuthStatus(root, "正在通过企业微信 OAuth 换取登录态...");
    const url = `${base}/api/auth/wecom/callback?code=${encodeURIComponent(code)}`;
    try {
      const response = await requestWithTimeout(url, { method: "GET" }, config.requestTimeoutMs);
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        // 若后端未配置 OAuth（503）或账号未绑定（401），降级提示并尝试短票据
        const errMsg = (data && data.detail) ? data.detail : `HTTP ${response.status}`;
        if (response.status === 503 || response.status === 401) {
          setAuthStatus(root, `OAuth 换码降级：${errMsg}。请改用短期票据链接。`, true);
        } else {
          throw new Error(errMsg);
        }
      } else {
        config.token = data.access_token || "";
        saveRuntimeConfig(config.baseUrl, config.token, config);
        bindRuntimeFields(root, config);
        cleanupSensitiveQuery();
        setAuthStatus(root, `企业微信授权成功，当前用户：${data.user?.username || "未知"}`);
        return data;
      }
    } catch (error) {
      bindRuntimeFields(root, config);
      // OAuth 失败后不立即 throw，允许页面继续（可能已有 localStorage token）
      setAuthStatus(root, `OAuth 换码失败：${error.message}。如有本地 Token 仍可提交。`, true);
    }
    cleanupSensitiveQuery();
    saveRuntimeConfig(config.baseUrl, config.token, config);
    bindRuntimeFields(root, config);
    return null;
  }

  // ── 次级：短期票据（管理员从桌面端下发）────────────────────────────────
  if (ticket) {
    setAuthStatus(root, "正在校验移动授权票据...");
    const url = `${base}/api/auth/mobile-h5/exchange?ticket=${encodeURIComponent(ticket)}`;
    try {
      const response = await requestWithTimeout(url, { method: "GET" }, config.requestTimeoutMs);
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        throw new Error(formatErrorMessage(response.status, data));
      }
      config.token = data.access_token || "";
      saveRuntimeConfig(config.baseUrl, config.token, config);
      bindRuntimeFields(root, config);
      cleanupSensitiveQuery();
      setAuthStatus(root, `票据授权成功，当前用户：${data.user?.username || "未知"}`);
      return data;
    } catch (error) {
      bindRuntimeFields(root, config);
      setAuthStatus(root, `票据授权失败：${error.message || "票据无效"}`, true);
      throw error;
    }
  }

  // ── 兜底：本地 localStorage token 或未登录 ─────────────────────────────
  saveRuntimeConfig(config.baseUrl, config.token, config);
  bindRuntimeFields(root, config);
  cleanupSensitiveQuery();
  if (config.token) {
    setAuthStatus(root, "已检测到本地登录态，可直接提交。");
  } else {
    setAuthStatus(root, "未登录。请通过企业微信应用链接进入，或联系管理员发放短期票据。", true);
  }
  return null;
}

/**
 * 构造企业微信网页授权跳转链接。
 * @param {string} corpId       - 企业 CorpID
 * @param {string} redirectUri  - 完整回调 URL（需在企业微信后台配置可信域名）
 * @param {string} [state]      - 透传状态，可选
 */
export function buildWecomOAuthUrl(corpId, redirectUri, state = "") {
  const params = new URLSearchParams({
    appid: corpId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "snsapi_base",
  });
  if (state) params.set("state", state);
  return `https://open.weixin.qq.com/connect/oauth2/authorize?${params.toString()}#wechat_redirect`;
}

export async function callApi({
  baseUrl,
  token,
  path,
  method = "GET",
  body,
  isForm = false,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  maxRetries = DEFAULT_MAX_RETRIES,
  requestKey,
}) {
  const normalizedBaseUrl = (baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!isForm) headers["Content-Type"] = "application/json";

  if (requestKey && pendingRequestKeys.has(requestKey)) {
    throw new Error("请求仍在处理中，请勿重复提交");
  }

  if (requestKey) pendingRequestKeys.add(requestKey);

  let lastError = null;
  const retries = Math.max(0, Math.min(3, Number(maxRetries || 0)));
  const requestTimeout = toSafePositiveNumber(timeoutMs, DEFAULT_TIMEOUT_MS);

  try {
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      try {
        const resp = await requestWithTimeout(`${normalizedBaseUrl}${path}`, {
          method,
          headers,
          body: isForm ? body : body ? JSON.stringify(body) : undefined,
        }, requestTimeout);

        const text = await resp.text();
        let data;
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = text;
        }

        if (!resp.ok) {
          const message = formatErrorMessage(resp.status, data);
          if (resp.status === 401) {
            localStorage.removeItem("zhk_h5_token");
            throw new Error("401 未授权，请重新获取 mobile-h5 授权票据或更新 Token");
          }
          if (isRetryableStatus(resp.status) && attempt < retries) {
            await wait(400 * (attempt + 1));
            continue;
          }
          throw new Error(message);
        }

        return data;
      } catch (error) {
        lastError = error;
        const aborted = error?.name === "AbortError";
        const offline = typeof navigator !== "undefined" && navigator.onLine === false;
        if (offline) {
          throw new Error("当前网络不可用，请恢复连接后重试");
        }
        if ((aborted || attempt < retries) && attempt < retries) {
          await wait(400 * (attempt + 1));
          continue;
        }
      }
    }
  } finally {
    if (requestKey) pendingRequestKeys.delete(requestKey);
  }

  if (lastError?.name === "AbortError") {
    throw new Error("请求超时，请检查弱网环境或调大超时设置后重试");
  }
  throw lastError || new Error("请求失败");
}

function bindRuntimeFields(root, config) {
  if (root.querySelector("#baseUrl")) root.querySelector("#baseUrl").value = config.baseUrl;
  if (root.querySelector("#token")) root.querySelector("#token").value = config.token;
  if (root.querySelector("#timeoutMs")) root.querySelector("#timeoutMs").value = String(config.requestTimeoutMs);
  if (root.querySelector("#maxRetries")) root.querySelector("#maxRetries").value = String(config.maxRetries);
}

export function bindGlobalConfig(root) {
  const config = loadRuntimeConfig();
  bindRuntimeFields(root, config);

  root.querySelector("#saveConfig")?.addEventListener("click", () => {
    const nextConfig = getConfigFromPage(root);
    saveRuntimeConfig(nextConfig.baseUrl, nextConfig.token, nextConfig);
    setStatus(root, `配置已保存\nbaseUrl=${nextConfig.baseUrl}\ntimeoutMs=${nextConfig.requestTimeoutMs}\nmaxRetries=${nextConfig.maxRetries}`);
    setAuthStatus(root, nextConfig.token ? "已保存本地登录态。" : "未保存 Token，仅保留接口配置。", !nextConfig.token);
  });
}

export function getConfigFromPage(root) {
  return {
    baseUrl: (root.querySelector("#baseUrl")?.value || DEFAULT_BASE_URL).trim(),
    token: (root.querySelector("#token")?.value || "").trim(),
    requestTimeoutMs: toSafePositiveNumber(root.querySelector("#timeoutMs")?.value, DEFAULT_TIMEOUT_MS),
    maxRetries: Math.max(0, Math.min(3, Number(root.querySelector("#maxRetries")?.value || DEFAULT_MAX_RETRIES))),
  };
}

export function buildClientRequestId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function setButtonBusy(button, busy, busyText, idleText) {
  if (!button) return;
  button.disabled = busy;
  button.textContent = busy ? busyText : idleText;
}

export function setAuthStatus(root, content, isError = false) {
  const box = root.querySelector("#authStatus");
  if (!box) return;
  box.className = isError ? "status error auth-status" : "status auth-status";
  box.textContent = content;
}

export function setStatus(root, content, isError = false) {
  const box = root.querySelector("#status");
  box.className = isError ? "status error" : "status";
  box.textContent = content;
}
