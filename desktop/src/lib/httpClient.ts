/**
 * HTTP 客户端核心模块
 * 提供 Axios 实例和原生 fetch 工具函数
 */
import axios from 'axios';
import { clearToken, getToken } from './auth';

/**
 * 解析 API 基础 URL
 * 优先级: localStorage runtime > 环境变量 > 开发环境默认 > 生产环境相对路径
 */
export function resolveApiBaseUrl(): string {
  const isElectron = typeof window !== "undefined" && !!(window as any).desktop?.isElectron;
  const isDev = import.meta.env.DEV;
  
  if (typeof window !== "undefined") {
    const runtimeBase = localStorage.getItem("zhk_api_base_url");
    // Only Electron desktop should honor runtime localhost overrides.
    if (isElectron && runtimeBase) return runtimeBase;
  }
  
  // 环境变量优先
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase) return envBase;
  
  // 开发环境默认回退到本地后端
  if (isDev) return "http://localhost:8000";
  
  // 生产环境使用相对路径（同源访问）
  return "";
}

// ═══════════ Axios 实例 ═══════════

/**
 * Axios 实例 - 用于 lib/api.ts 中的业务 API 函数
 * 自动注入 token，处理 401 响应
 */
const httpClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 20000
});

// 请求拦截器 - 自动注入 token
httpClient.interceptors.request.use((config) => {
  config.baseURL = resolveApiBaseUrl();
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 - 处理 401 自动登出
httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken("expired");
    }
    // 确保错误始终被 reject，不会静默吞掉
    return Promise.reject(error);
  }
);

export default httpClient;

// ═══════════ 原生 fetch 工具函数 ═══════════

/**
 * 获取认证请求头
 * 用于原生 fetch 调用
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * 获取 API 基础 URL
 * Electron 首次配置完成后端口可能变化，因此这里不做缓存。
 */
export function getApiBase(): string {
  return resolveApiBaseUrl();
}

/**
 * 通用 API 请求方法（原生 fetch 版本）
 * 用于 api/*.ts 中的模块化 API
 */
export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T | null> {
  try {
    const resp = await fetch(`${getApiBase()}${url}`, {
      ...options,
      headers: {
        ...getAuthHeaders(),
        ...(options?.headers || {}),
      },
    });
    if (resp.status === 401) {
      clearToken("expired");
      return null;
    }
    if (!resp.ok) {
      console.warn(`API HTTP ${resp.status}: ${url}`);
      return null;
    }
    return await resp.json();
  } catch (e) {
    console.warn('API call failed:', e);
    return null;
  }
}

/**
 * 确保 API 返回结果非空
 * 用于抛出带有明确错误信息的异常
 */
export function requireApiResult<T>(data: T | null, errorMessage: string): T {
  if (data === null) {
    throw new Error(errorMessage);
  }
  return data;
}
