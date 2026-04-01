// 线索 API 模块
// 对接 /api/lead/* 所有端点
import { apiFetch, requireApiResult } from '../lib/httpClient';

// 类型定义
export interface Lead {
  id: number;
  owner_id: number;
  platform: string;
  source: string;
  source_content_id?: number;
  publish_task_id?: number;
  title?: string;
  post_url?: string;
  wechat_adds: number;
  leads: number;
  valid_leads: number;
  conversions: number;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
  intention_level: 'low' | 'medium' | 'high';
  note?: string;
  customer_id?: number;
  created_at: string;
  updated_at: string;
}

export interface LeadAttributionStats {
  by_platform: Array<{
    platform: string;
    lead_count: number;
    valid_count: number;
    conversion_count: number;
    conversion_rate: number;
  }>;
  by_source: Array<{
    source: string;
    lead_count: number;
    valid_count: number;
    conversion_count: number;
    conversion_rate: number;
  }>;
  top_content: Array<{
    title: string;
    platform: string;
    lead_count: number;
    conversions: number;
  }>;
  period_days: number;
}

export interface LeadFunnelStats {
  stages: Array<{
    stage: string;
    stage_label: string;
    count: number;
    rate: number;
  }>;
  period_days: number;
}

export interface LeadTrace {
  id: number;
  owner_id: number;
  platform: string;
  source: string;
  status: string;
  intention_level: string;
  customer_id?: number;
  publish_record_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateLeadRequest {
  platform: string;
  source: string;
  source_content_id?: number;
  publish_task_id?: number;
  title?: string;
  post_url?: string;
  wechat_adds?: number;
  leads?: number;
  valid_leads?: number;
  conversions?: number;
  status?: string;
  intention_level: string;
  note?: string;
}

export interface UpdateLeadStatusRequest {
  status: string;
}

export interface AssignLeadRequest {
  owner_id?: number;
}

export interface ConvertLeadToCustomerRequest {
  nickname?: string;
  wechat_id?: string;
  phone?: string;
  intention_level?: string;
  tags?: string[];
  inquiry_content?: string;
}

export interface ListLeadsParams {
  status?: string;
  owner_id?: number;
  skip?: number;
  limit?: number;
}

export const leadApi = {
  /**
   * 创建线索
   */
  async create(request: CreateLeadRequest): Promise<Lead> {
    const data = await apiFetch<Lead>('/api/lead/create', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建线索失败');
  },

  /**
   * 获取线索列表
   */
  async list(params?: ListLeadsParams): Promise<Lead[]> {
    const query = new URLSearchParams();
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    if (params?.owner_id !== undefined) query.set('owner_id', String(params.owner_id));
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<Lead[]>(`/api/lead/list?${query}`);
    return requireApiResult(data, '获取线索列表失败');
  },

  /**
   * 更新线索状态
   */
  async updateStatus(leadId: number, status: string): Promise<Lead> {
    const data = await apiFetch<Lead>(`/api/lead/${leadId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
    return requireApiResult(data, '更新线索状态失败');
  },

  /**
   * 分配线索负责人
   */
  async assignOwner(leadId: number, ownerId?: number): Promise<Lead> {
    const data = await apiFetch<Lead>(`/api/lead/${leadId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ owner_id: ownerId }),
    });
    return requireApiResult(data, '分配线索负责人失败');
  },

  /**
   * 获取线索追踪链路
   */
  async getTrace(leadId: number): Promise<LeadTrace> {
    const data = await apiFetch<LeadTrace>(`/api/lead/${leadId}/trace`);
    return requireApiResult(data, '获取线索追踪链路失败');
  },

  /**
   * 将线索转化为客户
   */
  async convertToCustomer(leadId: number, request?: ConvertLeadToCustomerRequest): Promise<unknown> {
    const data = await apiFetch<unknown>(`/api/lead/${leadId}/convert-customer`, {
      method: 'POST',
      body: JSON.stringify(request || {}),
    });
    return requireApiResult(data, '转化线索为客户失败');
  },

  /**
   * 获取线索归因统计
   */
  async getAttributionStats(days?: number): Promise<LeadAttributionStats> {
    const query = days !== undefined ? `?days=${days}` : '';
    const data = await apiFetch<LeadAttributionStats>(`/api/lead/stats/attribution${query}`);
    return requireApiResult(data, '获取线索归因统计失败');
  },

  /**
   * 获取转化漏斗统计
   */
  async getFunnelStats(days?: number): Promise<LeadFunnelStats> {
    const query = days !== undefined ? `?days=${days}` : '';
    const data = await apiFetch<LeadFunnelStats>(`/api/lead/stats/funnel${query}`);
    return requireApiResult(data, '获取转化漏斗统计失败');
  },
};

export default leadApi;
