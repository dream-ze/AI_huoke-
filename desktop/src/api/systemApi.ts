import { apiFetch, requireApiResult } from '../lib/httpClient';
import { apiRoutes } from './routes';

export interface SystemVersionInfo {
  api_version: string;
  app_name: string;
  release_channel: string;
  min_desktop_version: string;
  latest_desktop_version: string;
}

export interface SystemHealthInfo {
  status: string;
  timestamp_utc?: string;
  checks?: Record<string, unknown>;
  runtime?: Record<string, unknown>;
}

export const systemApi = {
  async getVersion(): Promise<SystemVersionInfo> {
    const data = await apiFetch<SystemVersionInfo>(apiRoutes.system.version);
    return requireApiResult(data, '获取系统版本失败');
  },

  async getHealth(): Promise<SystemHealthInfo> {
    const data = await apiFetch<SystemHealthInfo>(apiRoutes.system.opsHealth);
    return requireApiResult(data, '获取系统健康状态失败');
  },
};

export default systemApi;
