import { useAuthStore, migrateOldAuth } from '../store';

const REDIRECT_PATH_KEY = "zhk_redirect_path";
const LOGOUT_EVENT = "zhk-auth-logout";

// 确保数据迁移执行
if (typeof window !== 'undefined') {
  migrateOldAuth();
}

export function getToken(): string | null {
  return useAuthStore.getState().token;
}

export function setToken(token: string): void {
  useAuthStore.getState().setToken(token);
}

export function clearToken(reason?: "expired" | "manual"): void {
  useAuthStore.getState().logout();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT, { detail: { reason: reason || "manual" } }));
  }
}

export function isLoggedIn(): boolean {
  return useAuthStore.getState().isAuthenticated;
}

export function saveRedirectPath(path: string): void {
  if (!path || path === "/login") return;
  localStorage.setItem(REDIRECT_PATH_KEY, path);
}

export function consumeRedirectPath(defaultPath = "/dashboard"): string {
  const path = localStorage.getItem(REDIRECT_PATH_KEY) || defaultPath;
  localStorage.removeItem(REDIRECT_PATH_KEY);
  return path;
}

export function getLogoutEventName(): string {
  return LOGOUT_EVENT;
}

// 导出user相关操作
export function getUser() {
  return useAuthStore.getState().user;
}

export function setUser(user: any): void {
  useAuthStore.getState().setUser(user);
}

export function login(token: string, user: any): void {
  useAuthStore.getState().login(token, user);
}
