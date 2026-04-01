// 客户 API 模块
// 对接 /api/customer/* 所有端点
import { apiFetch, requireApiResult, getAuthHeaders, getApiBase } from '../lib/httpClient';
import { apiRoutes } from './routes';

// 类型定义
export interface Customer {
  id: number;
  owner_id: number;
  nickname: string;
  wechat_id?: string;
  phone?: string;
  email?: string;
  company?: string;
  position?: string;
  industry?: string;
  deal_value?: number;
  address?: string;
  source_platform: string;
  source_content_id?: number;
  lead_id?: number;
  tags: string[];
  intention_level: 'low' | 'medium' | 'high';
  inquiry_content?: string;
  customer_status: 'new' | 'following' | 'negotiating' | 'converted' | 'lost';
  last_follow_at?: string;
  follow_count: number;
  created_at: string;
  updated_at: string;
}

export interface FollowRecord {
  id: number;
  customer_id: number;
  content: string;
  created_by: number;
  created_at: string;
}

export interface CreateCustomerRequest {
  nickname: string;
  wechat_id?: string;
  phone?: string;
  email?: string;
  company?: string;
  position?: string;
  industry?: string;
  deal_value?: number;
  address?: string;
  source_platform: string;
  source_content_id?: number;
  lead_id?: number;
  tags: string[];
  intention_level: string;
  inquiry_content?: string;
}

export interface UpdateCustomerRequest {
  nickname?: string;
  wechat_id?: string;
  phone?: string;
  email?: string;
  company?: string;
  position?: string;
  industry?: string;
  deal_value?: number;
  address?: string;
  tags?: string[];
  intention_level?: string;
  inquiry_content?: string;
  customer_status?: string;
}

export interface AddFollowRecordRequest {
  content: string;
}

export interface ListCustomersParams {
  status?: string;
  skip?: number;
  limit?: number;
}

export const customerApi = {
  /**
   * 创建客户
   */
  async create(request: CreateCustomerRequest): Promise<Customer> {
    const data = await apiFetch<Customer>(apiRoutes.customer.create, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建客户失败');
  },

  /**
   * 获取客户列表
   */
  async list(params?: ListCustomersParams): Promise<Customer[]> {
    const query = new URLSearchParams();
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<Customer[]>(`${apiRoutes.customer.list}?${query}`);
    return requireApiResult(data, '获取客户列表失败');
  },

  /**
   * 获取客户详情
   */
  async getDetail(customerId: number): Promise<Customer> {
    const data = await apiFetch<Customer>(apiRoutes.customer.detail(customerId));
    return requireApiResult(data, '获取客户详情失败');
  },

  /**
   * 更新客户
   */
  async update(customerId: number, request: UpdateCustomerRequest): Promise<Customer> {
    const data = await apiFetch<Customer>(apiRoutes.customer.detail(customerId), {
      method: 'PUT',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '更新客户失败');
  },

  /**
   * 添加跟进记录
   */
  async addFollowRecord(customerId: number, content: string): Promise<Customer> {
    const data = await apiFetch<Customer>(apiRoutes.customer.follow(customerId), {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    return requireApiResult(data, '添加跟进记录失败');
  },

  /**
   * 删除客户
   */
  async delete(customerId: number): Promise<{ message: string }> {
    const data = await apiFetch<{ message: string }>(apiRoutes.customer.detail(customerId), {
      method: 'DELETE',
    });
    return requireApiResult(data, '删除客户失败');
  },

  /**
   * 获取待跟进客户列表
   */
  async getPendingList(limit?: number): Promise<Customer[]> {
    const query = limit !== undefined ? `?limit=${limit}` : '';
    const data = await apiFetch<Customer[]>(`${apiRoutes.customer.pendingList}${query}`);
    return requireApiResult(data, '获取待跟进客户列表失败');
  },

  /**
   * 导出客户 CSV
   */
  async exportCsv(status?: string): Promise<Blob> {
    const query = status ? `?status=${status}` : '';
    const resp = await fetch(`${getApiBase()}${apiRoutes.customer.exportCsv}${query}`, {
      headers: getAuthHeaders(),
    });
    if (!resp.ok) {
      throw new Error('导出客户 CSV 失败');
    }
    return resp.blob();
  },
};

export default customerApi;
