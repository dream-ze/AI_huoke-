// 发布任务 API 模块
// 对接 /api/publish/* 所有端点
import { apiFetch, requireApiResult, getAuthHeaders, getApiBase } from '../lib/httpClient';
import { apiRoutes } from './routes';
import type { ContentLeadStats, AccountLeadStats, TrackingCodeResult } from '../types';

// 类型定义
export interface PublishRecord {
  id: number;
  rewritten_content_id: number;
  platform: string;
  account_name: string;
  publish_time?: string;
  views?: number;
  likes?: number;
  comments?: number;
  favorites?: number;
  shares?: number;
  private_messages?: number;
  wechat_adds?: number;
  leads?: number;
  valid_leads?: number;
  conversions?: number;
  published_by?: string;
  created_at?: string;
}

export interface PublishTask {
  id: number;
  owner_id: number;
  rewritten_content_id?: number;
  platform: string;
  account_name: string;
  task_title: string;
  content_text: string;
  status: 'pending' | 'claimed' | 'submitted' | 'rejected' | 'closed';
  assigned_to?: number;
  post_url?: string;
  posted_at?: string;
  views?: number;
  likes?: number;
  comments?: number;
  favorites?: number;
  shares?: number;
  private_messages?: number;
  wechat_adds?: number;
  leads?: number;
  valid_leads?: number;
  conversions?: number;
  reject_reason?: string;
  close_reason?: string;
  claimed_at?: string;
  closed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PublishTaskStats {
  total: number;
  pending: number;
  claimed: number;
  submitted: number;
  rejected: number;
  closed: number;
}

export interface PublishTaskTrace {
  task_id: number;
  publish_record_id?: number;
  lead_id?: number;
  customer_id?: number;
}

export interface PlatformStats {
  platform: string;
  total_tasks: number;
  completed_tasks: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_wechat_adds: number;
  total_leads: number;
  total_valid_leads: number;
  total_conversions: number;
  avg_views_per_task: number;
  conversion_rate: number;
}

export interface RoiTrendItem {
  date: string;
  publish_count: number;
  total_leads: number;
  total_valid_leads: number;
  total_conversions: number;
  lead_rate: number;
  conversion_rate: number;
}

export interface ContentAnalysisItem {
  platform: string;
  task_count: number;
  avg_views: number;
  avg_likes: number;
  avg_wechat_adds: number;
  avg_conversions: number;
  best_task_title: string | null;
  best_task_conversions: number;
}

export interface CreatePublishRecordRequest {
  rewritten_content_id: number;
  platform: string;
  account_name: string;
}

export interface CreatePublishTaskRequest {
  rewritten_content_id?: number;
  platform: string;
  account_name: string;
  task_title: string;
  content_text: string;
  assigned_to?: number;
  due_time?: string;
}

export interface SubmitPublishTaskRequest {
  post_url?: string;
  posted_at?: string;
  views?: number;
  likes?: number;
  comments?: number;
  favorites?: number;
  shares?: number;
  private_messages?: number;
  wechat_adds?: number;
  leads?: number;
  valid_leads?: number;
  conversions?: number;
  note?: string;
}

export interface AssignPublishTaskRequest {
  assigned_to: number;
  note?: string;
}

export interface PublishTaskActionRequest {
  note?: string;
}

export interface ListPublishTasksParams {
  status?: string;
  platform?: string;
  assigned_to?: number;
  skip?: number;
  limit?: number;
}

export const publishApi = {
  /**
   * 创建发布记录
   */
  async createRecord(request: CreatePublishRecordRequest): Promise<PublishRecord> {
    const data = await apiFetch<PublishRecord>(apiRoutes.publish.create, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建发布记录失败');
  },

  /**
   * 获取发布记录列表
   */
  async listRecords(params?: { platform?: string; skip?: number; limit?: number }): Promise<PublishRecord[]> {
    const query = new URLSearchParams();
    if (params?.platform) query.set('platform', params.platform);
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<PublishRecord[]>(`${apiRoutes.publish.list}?${query}`);
    return requireApiResult(data, '获取发布记录列表失败');
  },

  /**
   * 获取发布记录详情
   */
  async getRecord(recordId: number): Promise<PublishRecord> {
    const data = await apiFetch<PublishRecord>(apiRoutes.publish.detail(recordId));
    return requireApiResult(data, '获取发布记录详情失败');
  },

  /**
   * 更新发布记录
   */
  async updateRecord(recordId: number, updates: Partial<PublishRecord>): Promise<PublishRecord> {
    const data = await apiFetch<PublishRecord>(apiRoutes.publish.detail(recordId), {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    return requireApiResult(data, '更新发布记录失败');
  },

  /**
   * 创建发布任务
   */
  async createTask(request: CreatePublishTaskRequest): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.tasksCreate, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建发布任务失败');
  },

  /**
   * 获取发布任务列表
   */
  async listTasks(params?: ListPublishTasksParams): Promise<PublishTask[]> {
    const query = new URLSearchParams();
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    if (params?.platform && params.platform !== 'all') query.set('platform', params.platform);
    if (params?.assigned_to !== undefined) query.set('assigned_to', String(params.assigned_to));
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<PublishTask[]>(`${apiRoutes.publish.tasksList}?${query}`);
    return requireApiResult(data, '获取发布任务列表失败');
  },

  /**
   * 获取发布任务详情
   */
  async getTask(taskId: number): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskDetail(taskId));
    return requireApiResult(data, '获取发布任务详情失败');
  },

  /**
   * 获取任务统计
   */
  async getTaskStats(): Promise<PublishTaskStats> {
    const data = await apiFetch<PublishTaskStats>(apiRoutes.publish.tasksStats);
    return requireApiResult(data, '获取任务统计失败');
  },

  /**
   * 获取任务追踪链路
   */
  async getTaskTrace(taskId: number): Promise<PublishTaskTrace> {
    const data = await apiFetch<PublishTaskTrace>(apiRoutes.publish.taskTrace(taskId));
    return requireApiResult(data, '获取任务追踪链路失败');
  },

  /**
   * 认领任务
   */
  async claimTask(taskId: number, note?: string): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskClaim(taskId), {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    return requireApiResult(data, '认领任务失败');
  },

  /**
   * 分配任务
   */
  async assignTask(taskId: number, request: AssignPublishTaskRequest): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskAssign(taskId), {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '分配任务失败');
  },

  /**
   * 提交任务
   */
  async submitTask(taskId: number, request: SubmitPublishTaskRequest): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskSubmit(taskId), {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '提交任务失败');
  },

  /**
   * 驳回任务
   */
  async rejectTask(taskId: number, note?: string): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskReject(taskId), {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    return requireApiResult(data, '驳回任务失败');
  },

  /**
   * 关闭任务
   */
  async closeTask(taskId: number, note?: string): Promise<PublishTask> {
    const data = await apiFetch<PublishTask>(apiRoutes.publish.taskClose(taskId), {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
    return requireApiResult(data, '关闭任务失败');
  },

  /**
   * 导出任务 CSV
   */
  async exportTasksCsv(params?: { status?: string; platform?: string }): Promise<Blob> {
    const query = new URLSearchParams();
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    if (params?.platform && params.platform !== 'all') query.set('platform', params.platform);
    const resp = await fetch(`${getApiBase()}${apiRoutes.publish.tasksExportCsv}?${query}`, {
      headers: getAuthHeaders(),
    });
    if (!resp.ok) {
      throw new Error('导出任务 CSV 失败');
    }
    return resp.blob();
  },

  /**
   * 获取平台统计
   */
  async getStatsByPlatform(days?: number): Promise<PlatformStats[]> {
    const query = days !== undefined ? `?days=${days}` : '';
    const data = await apiFetch<PlatformStats[]>(`${apiRoutes.publish.statsByPlatform}${query}`);
    return requireApiResult(data, '获取平台统计失败');
  },

  /**
   * 获取 ROI 趋势
   */
  async getRoiTrend(days?: number): Promise<RoiTrendItem[]> {
    const query = days !== undefined ? `?days=${days}` : '';
    const data = await apiFetch<RoiTrendItem[]>(`${apiRoutes.publish.roiTrend}${query}`);
    return requireApiResult(data, '获取 ROI 趋势失败');
  },

  /**
   * 获取内容分析
   */
  async getContentAnalysis(days?: number): Promise<ContentAnalysisItem[]> {
    const query = days !== undefined ? `?days=${days}` : '';
    const data = await apiFetch<ContentAnalysisItem[]>(`${apiRoutes.publish.contentAnalysis}${query}`);
    return requireApiResult(data, '获取内容分析失败');
  },

  /**
   * 通过追踪码查询发布内容和关联线索
   */
  async getContentByTrackingCode(trackingCode: string): Promise<TrackingCodeResult> {
    const data = await apiFetch<TrackingCodeResult>(apiRoutes.publish.track(trackingCode));
    return requireApiResult(data, '追踪码查询失败');
  },

  /**
   * 获取账号维度的线索统计
   */
  async getAccountLeadStats(
    accountId: number,
    dateRange?: { start_date: string; end_date: string }
  ): Promise<AccountLeadStats> {
    const query = new URLSearchParams();
    if (dateRange?.start_date) query.set('start_date', dateRange.start_date);
    if (dateRange?.end_date) query.set('end_date', dateRange.end_date);
    const queryString = query.toString();
    const data = await apiFetch<AccountLeadStats>(
      `${apiRoutes.publish.accountLeads(accountId)}${queryString ? `?${queryString}` : ''}`
    );
    return requireApiResult(data, '获取账号线索统计失败');
  },

  /**
   * 获取内容维度的线索统计
   */
  async getContentLeadStats(contentId: number): Promise<ContentLeadStats> {
    const data = await apiFetch<ContentLeadStats>(apiRoutes.publish.contentLeads(contentId));
    return requireApiResult(data, '获取内容线索统计失败');
  },
};

export default publishApi;
