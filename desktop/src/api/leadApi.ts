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
  // ABCD 分级
  grade?: 'A' | 'B' | 'C' | 'D';
  grade_score?: number;
  // 归因字段
  campaign_id?: number;
  publish_account_id?: number;
  published_content_id?: number;
  generation_task_id?: number;
  attribution_chain?: {
    platform?: string;
    account_id?: number;
    content_id?: number;
    campaign_id?: number;
    channel?: string;
    audience_tags?: string[];
  };
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

export interface ConvertLeadToCustomerResponse {
  id: number;
  lead_id: number;
  [key: string]: unknown;
}

export interface ListLeadsParams {
  status?: string;
  owner_id?: number;
  skip?: number;
  limit?: number;
  grade?: 'A' | 'B' | 'C' | 'D';
}

// 从发布内容创建线索的请求
export interface LeadFromPublishRequest {
  published_content_id: number;
  platform: string;
  contact_info: {
    phone?: string;
    wechat?: string;
  };
  channel: string;
  audience_tags?: string[];
  notes?: string;
}

// 从发布内容创建线索的响应
export interface LeadFromPublishResponse {
  lead: Lead;
  attribution: {
    attribution_id: number | null;
    chain: LeadAttributionChain;
  };
  scoring: {
    score: number;
    grade: string;
    factors: Record<string, number>;
  };
}

// 归因链响应
export interface LeadAttributionChain {
  lead_id: number;
  platform?: string;
  account_name?: string;
  content_title?: string;
  campaign_name?: string;
  audience_tags: string[];
  topic_tags: string[];
  channel?: string;
  first_contact_time?: string;
  current_stage: string;
  conversion_result?: string;
  touchpoint_url?: string;
}

// 批量导入线索请求
export interface BatchImportLeadItem {
  platform: string;
  title: string;
  source?: string;
  post_url?: string;
  wechat_adds?: number;
  leads?: number;
  valid_leads?: number;
  conversions?: number;
  status?: string;
  intention_level?: string;
  note?: string;
}

// 批量导入线索响应
export interface BatchImportResponse {
  total: number;
  success: number;
  failed: number;
  duplicates: number;
  created_ids: number[];
  failed_details: Array<{
    index: number;
    error: string;
  data: BatchImportLeadItem;
  }>;
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
  async convertToCustomer(leadId: number, request?: ConvertLeadToCustomerRequest): Promise<ConvertLeadToCustomerResponse> {
    const data = await apiFetch<ConvertLeadToCustomerResponse>(`/api/lead/${leadId}/convert-customer`, {
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

  /**
   * 从发布内容创建线索
   */
  async createLeadFromPublish(request: LeadFromPublishRequest): Promise<LeadFromPublishResponse> {
    const data = await apiFetch<LeadFromPublishResponse>('/api/lead/from-publish', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '从发布内容创建线索失败');
  },

  /**
   * 批量导入线索
   */
  async batchImportLeads(leads: BatchImportLeadItem[]): Promise<BatchImportResponse> {
    const data = await apiFetch<BatchImportResponse>('/api/lead/batch-import-v2', {
      method: 'POST',
      body: JSON.stringify({ leads }),
    });
    return requireApiResult(data, '批量导入线索失败');
  },

  /**
   * 获取线索归因链
   */
  async getLeadAttribution(leadId: number): Promise<LeadAttributionChain> {
    const data = await apiFetch<LeadAttributionChain>(`/api/lead/${leadId}/attribution`);
    return requireApiResult(data, '获取线索归因链失败');
  },

  /**
   * 按分级查询线索
   */
  async getLeadsByGrade(grade: 'A' | 'B' | 'C' | 'D', skip?: number, limit?: number): Promise<Lead[]> {
    const query = new URLSearchParams();
    if (skip !== undefined) query.set('skip', String(skip));
    if (limit !== undefined) query.set('limit', String(limit));
    const data = await apiFetch<Lead[]>(`/api/lead/stats/by-grade/${grade}?${query}`);
    return requireApiResult(data, '按分级查询线索失败');
  },
};

export default leadApi;
