// 社交账号管理 API 模块
// 对接 /api/social/* 所有端点
import { apiFetch, requireApiResult } from '../lib/httpClient';
import { apiRoutes } from './routes';

// 类型定义
export interface SocialAccount {
  id: number;
  owner_id: number;
  platform: string;
  account_id: string | null;
  account_name: string;
  avatar_url: string | null;
  status: 'active' | 'inactive' | 'suspended';
  followers_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SocialPlatform {
  value: string;
  label: string;
}

export interface CreateSocialAccountRequest {
  platform: string;
  account_name: string;
  account_id?: string;
  avatar_url?: string;
  notes?: string;
}

export interface UpdateSocialAccountRequest {
  account_name?: string;
  account_id?: string;
  avatar_url?: string;
  status?: string;
  followers_count?: number;
  notes?: string;
}

export const socialAccountApi = {
  /**
   * 创建/绑定社交账号
   */
  async create(request: CreateSocialAccountRequest): Promise<SocialAccount> {
    const data = await apiFetch<SocialAccount>(apiRoutes.social.create, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建社交账号失败');
  },

  /**
   * 获取社交账号列表
   */
  async list(platform?: string): Promise<SocialAccount[]> {
    const query = platform ? `?platform=${platform}` : '';
    const data = await apiFetch<SocialAccount[]>(`${apiRoutes.social.list}${query}`);
    return requireApiResult(data, '获取社交账号列表失败');
  },

  /**
   * 获取社交账号详情
   */
  async getDetail(accountId: number): Promise<SocialAccount> {
    const data = await apiFetch<SocialAccount>(apiRoutes.social.detail(accountId));
    return requireApiResult(data, '获取社交账号详情失败');
  },

  /**
   * 更新社交账号
   */
  async update(accountId: number, request: UpdateSocialAccountRequest): Promise<SocialAccount> {
    const data = await apiFetch<SocialAccount>(apiRoutes.social.detail(accountId), {
      method: 'PUT',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '更新社交账号失败');
  },

  /**
   * 删除/解绑社交账号
   */
  async delete(accountId: number): Promise<{ message: string }> {
    const data = await apiFetch<{ message: string }>(apiRoutes.social.detail(accountId), {
      method: 'DELETE',
    });
    return requireApiResult(data, '删除社交账号失败');
  },

  /**
   * 获取支持的平台列表
   */
  async getPlatforms(): Promise<SocialPlatform[]> {
    const data = await apiFetch<SocialPlatform[]>(apiRoutes.social.platforms);
    return requireApiResult(data, '获取平台列表失败');
  },
};

export default socialAccountApi;
