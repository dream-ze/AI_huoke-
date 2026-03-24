const TOKEN_KEY = "zhk_token";
const REDIRECT_PATH_KEY = "zhk_redirect_path";
const LOGOUT_EVENT = "zhk-auth-logout";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(reason?: "expired" | "manual"): void {
  localStorage.removeItem(TOKEN_KEY);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT, { detail: { reason: reason || "manual" } }));
  }
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
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
