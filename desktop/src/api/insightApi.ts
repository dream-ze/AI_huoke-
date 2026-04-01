// 爆款内容采集分析中心 API 模块
// 对接 /api/insight/* 所有端点
import { apiFetch, requireApiResult } from '../lib/httpClient';
import { apiRoutes } from './routes';

// 类型定义
export interface InsightTopic {
  id: number;
  name: string;
  description?: string;
  platform_focus?: string[];
  audience_tags?: string[];
  risk_notes?: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface InsightContentItem {
  id: number;
  owner_id: number;
  platform: string;
  content_type: string;
  source_type: string;
  source_url?: string;
  title?: string;
  body_text?: string;
  author_name?: string;
  author_profile_url?: string;
  fans_count?: number;
  account_positioning?: string;
  like_count: number;
  comment_count: number;
  share_count: number;
  collect_count: number;
  view_count: number;
  publish_time?: string;
  topic_id?: number;
  topic_name?: string;
  audience_tags?: string[];
  manual_note?: string;
  is_hot: boolean;
  heat_tier?: string;
  ai_analyzed: boolean;
  ai_analysis?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface InsightAuthor {
  id: number;
  platform: string;
  author_id?: string;
  author_name: string;
  profile_url?: string;
  avatar_url?: string;
  fans_count?: number;
  account_positioning?: string;
  content_count: number;
  avg_like_count: number;
  viral_rate: number;
  created_at: string;
  updated_at: string;
}

export interface InsightAnalyzeResult {
  item_id: number;
  title_formula?: string;
  pain_points?: string[];
  content_structure?: string;
  writing_style?: string;
  hook_type?: string;
  cta_type?: string;
  audience_match?: string[];
  risk_level?: string;
  knowledge_ids?: number[];
  analyzed_at: string;
}

export interface InsightAnalyzeBatchTask {
  id: number;
  owner_id: number;
  platform: string;
  collect_mode: string;
  target_value?: string;
  status: string;
  result_count: number;
  notes?: string;
  run_at?: string;
  created_at: string;
  updated_at: string;
}

export interface InsightRetrieveResult {
  items: Array<{
    id: number;
    title?: string;
    platform: string;
    topic_name?: string;
    audience_tags?: string[];
    ai_analysis?: Record<string, unknown>;
  }>;
  total: number;
  limit: number;
}

export interface InsightStats {
  total_items: number;
  hot_items: number;
  analyzed_items: number;
  topic_count: number;
  author_count: number;
  platform_distribution: Record<string, number>;
  heat_distribution: Record<string, number>;
}

export interface CreateInsightTopicRequest {
  name: string;
  description?: string;
  platform_focus?: string[];
  audience_tags?: string[];
  risk_notes?: string;
}

export interface ImportInsightItemRequest {
  platform: string;
  title: string;
  body_text: string;
  source_url?: string;
  content_type?: string;
  author_name?: string;
  author_profile_url?: string;
  fans_count?: number;
  account_positioning?: string;
  like_count?: number;
  comment_count?: number;
  share_count?: number;
  collect_count?: number;
  view_count?: number;
  publish_time?: string;
  topic_name?: string;
  audience_tags?: string[];
  manual_note?: string;
  source_type?: string;
  raw_payload?: Record<string, unknown>;
}

export interface ImportInsightBatchRequest {
  items: ImportInsightItemRequest[];
}

export interface InsightRetrieveRequest {
  platform: string;
  topic_name?: string;
  audience_tags?: string[];
  limit?: number;
}

export interface ListInsightItemsParams {
  platform?: string;
  topic_id?: number;
  is_hot?: boolean;
  heat_tier?: string;
  ai_analyzed?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface BatchAnalyzeResponse {
  task_id: number;
  queued: number;
  not_found: number[];
  rate_limit: {
    limit: number;
    window_seconds: number;
  };
  message: string;
}

export const insightApi = {
  /**
   * 创建主题
   */
  async createTopic(request: CreateInsightTopicRequest): Promise<InsightTopic> {
    const data = await apiFetch<InsightTopic>(apiRoutes.insight.topics, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '创建主题失败');
  },

  /**
   * 获取主题列表
   */
  async listTopics(): Promise<InsightTopic[]> {
    const data = await apiFetch<InsightTopic[]>(apiRoutes.insight.topics);
    return requireApiResult(data, '获取主题列表失败');
  },

  /**
   * 获取主题详情
   */
  async getTopic(topicId: number): Promise<InsightTopic> {
    const data = await apiFetch<InsightTopic>(apiRoutes.insight.topicDetail(topicId));
    return requireApiResult(data, '获取主题详情失败');
  },

  /**
   * 导入单条内容
   */
  async importItem(request: ImportInsightItemRequest): Promise<InsightContentItem> {
    const data = await apiFetch<InsightContentItem>(apiRoutes.insight.import, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '导入内容失败');
  },

  /**
   * 批量导入内容
   */
  async importBatch(request: ImportInsightBatchRequest): Promise<{ imported: number; skipped: number; total: number }> {
    const data = await apiFetch<{ imported: number; skipped: number; total: number }>(apiRoutes.insight.importBatch, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '批量导入内容失败');
  },

  /**
   * 获取内容列表
   */
  async listItems(params?: ListInsightItemsParams): Promise<InsightContentItem[]> {
    const query = new URLSearchParams();
    if (params?.platform) query.set('platform', params.platform);
    if (params?.topic_id !== undefined) query.set('topic_id', String(params.topic_id));
    if (params?.is_hot !== undefined) query.set('is_hot', String(params.is_hot));
    if (params?.heat_tier) query.set('heat_tier', params.heat_tier);
    if (params?.ai_analyzed !== undefined) query.set('ai_analyzed', String(params.ai_analyzed));
    if (params?.search) query.set('search', params.search);
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<InsightContentItem[]>(`${apiRoutes.insight.list}?${query}`);
    return requireApiResult(data, '获取内容列表失败');
  },

  /**
   * 获取内容详情
   */
  async getItem(itemId: number): Promise<InsightContentItem> {
    const data = await apiFetch<InsightContentItem>(apiRoutes.insight.detail(itemId));
    return requireApiResult(data, '获取内容详情失败');
  },

  /**
   * 删除内容
   */
  async deleteItem(itemId: number): Promise<{ deleted: boolean }> {
    const data = await apiFetch<{ deleted: boolean }>(apiRoutes.insight.detail(itemId), {
      method: 'DELETE',
    });
    return requireApiResult(data, '删除内容失败');
  },

  /**
   * AI 分析单条内容
   */
  async analyzeItem(itemId: number): Promise<InsightAnalyzeResult> {
    const data = await apiFetch<InsightAnalyzeResult>(apiRoutes.insight.analyze(itemId), {
      method: 'POST',
    });
    return requireApiResult(data, 'AI 分析内容失败');
  },

  /**
   * 批量 AI 分析
   */
  async analyzeBatch(itemIds: number[]): Promise<BatchAnalyzeResponse> {
    const data = await apiFetch<BatchAnalyzeResponse>(apiRoutes.insight.analyzeBatch, {
      method: 'POST',
      body: JSON.stringify(itemIds),
    });
    return requireApiResult(data, '批量 AI 分析失败');
  },

  /**
   * 获取分析任务列表
   */
  async listAnalyzeTasks(params?: { skip?: number; limit?: number }): Promise<InsightAnalyzeBatchTask[]> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<InsightAnalyzeBatchTask[]>(`${apiRoutes.insight.analyzeTasks}?${query}`);
    return requireApiResult(data, '获取分析任务列表失败');
  },

  /**
   * 获取分析任务详情
   */
  async getAnalyzeTask(taskId: number): Promise<InsightAnalyzeBatchTask> {
    const data = await apiFetch<InsightAnalyzeBatchTask>(apiRoutes.insight.analyzeTaskDetail(taskId));
    return requireApiResult(data, '获取分析任务详情失败');
  },

  /**
   * 获取账号档案列表
   */
  async listAuthors(params?: { platform?: string; skip?: number; limit?: number }): Promise<InsightAuthor[]> {
    const query = new URLSearchParams();
    if (params?.platform) query.set('platform', params.platform);
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const data = await apiFetch<InsightAuthor[]>(`${apiRoutes.insight.authors}?${query}`);
    return requireApiResult(data, '获取账号档案列表失败');
  },

  /**
   * 获取账号详情
   */
  async getAuthor(authorId: number): Promise<InsightAuthor> {
    const data = await apiFetch<InsightAuthor>(apiRoutes.insight.authorDetail(authorId));
    return requireApiResult(data, '获取账号详情失败');
  },

  /**
   * 检索召回（给生成模块）
   */
  async retrieve(request: InsightRetrieveRequest): Promise<InsightRetrieveResult> {
    const data = await apiFetch<InsightRetrieveResult>(apiRoutes.insight.retrieve, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '检索召回失败');
  },

  /**
   * 获取统计数据
   */
  async getStats(): Promise<InsightStats> {
    const data = await apiFetch<InsightStats>(apiRoutes.insight.stats);
    return requireApiResult(data, '获取统计数据失败');
  },
};

export default insightApi;
