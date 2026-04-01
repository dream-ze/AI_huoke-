/**
 * 选题规划 API 模块
 * 对接后端 /api/topic/* 端点
 */
import { apiFetch, requireApiResult } from '../lib/httpClient';

// ========== 类型定义 ==========

export interface TopicPlan {
  id: number;
  owner_id: number;
  title: string;
  platform: string;
  target_audience?: string;
  content_type?: string;
  scheduled_date?: string;
  status: 'draft' | 'scheduled' | 'published' | 'archived';
  description?: string;
  created_at: string;
  updated_at: string;
  ideas?: TopicIdea[];
}

export interface TopicIdea {
  id: number;
  plan_id: number;
  title: string;
  description?: string;
  keywords?: string[];
  platform: string;
  status: 'pending' | 'accepted' | 'rejected' | 'used';
  source_type?: string;
  source_hot_topic_id?: number;
  created_at: string;
  updated_at: string;
}

export interface HotTopic {
  id: number;
  platform: string;
  category?: string;
  topic_name: string;
  description?: string;
  heat_score: number;
  trend_direction: 'up' | 'down' | 'stable';
  peak_time?: string;
  tags?: string[];
  expired_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TopicRecommendation {
  title: string;
  description: string;
  keywords: string[];
  reason: string;
}

export interface CalendarItem {
  date: string;
  plans: TopicPlan[];
  count: number;
}

export interface PlanListParams {
  platform?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface IdeaListParams {
  plan_id?: number;
  status?: string;
  platform?: string;
  page?: number;
  page_size?: number;
}

export interface HotTopicListParams {
  platform?: string;
  category?: string;
  limit?: number;
}

export interface CreatePlanData {
  title: string;
  platform: string;
  target_audience?: string;
  content_type?: string;
  scheduled_date?: string;
  description?: string;
}

export interface UpdatePlanData {
  title?: string;
  platform?: string;
  target_audience?: string;
  content_type?: string;
  scheduled_date?: string;
  status?: 'draft' | 'scheduled' | 'published' | 'archived';
  description?: string;
}

export interface CreateIdeaData {
  plan_id?: number;
  title: string;
  description?: string;
  keywords?: string[];
  platform: string;
  source_type?: string;
  source_hot_topic_id?: number;
}

export interface RecommendParams {
  platform: string;
  audience?: string;
  count?: number;
}

// ========== API 导出 ==========

export const topicApi = {
  // === 选题计划 ===
  
  /**
   * 获取选题计划列表
   */
  async listPlans(params?: PlanListParams): Promise<{ items: TopicPlan[]; total: number; page: number; page_size: number }> {
    const query = new URLSearchParams();
    if (params?.platform) query.set('platform', params.platform);
    if (params?.status) query.set('status', params.status);
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    
    const data = await apiFetch<{ items: TopicPlan[]; total: number; page: number; page_size: number }>(`/api/topic/plans?${query}`);
    return requireApiResult(data, '获取选题计划列表失败');
  },

  /**
   * 创建选题计划
   */
  async createPlan(data: CreatePlanData): Promise<TopicPlan> {
    const result = await apiFetch<TopicPlan>('/api/topic/plans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return requireApiResult(result, '创建选题计划失败');
  },

  /**
   * 获取选题计划详情
   */
  async getPlan(id: number): Promise<TopicPlan> {
    const data = await apiFetch<TopicPlan>(`/api/topic/plans/${id}`);
    return requireApiResult(data, '获取选题计划详情失败');
  },

  /**
   * 更新选题计划
   */
  async updatePlan(id: number, data: UpdatePlanData): Promise<TopicPlan> {
    const result = await apiFetch<TopicPlan>(`/api/topic/plans/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return requireApiResult(result, '更新选题计划失败');
  },

  /**
   * 删除选题计划
   */
  async deletePlan(id: number): Promise<{ message: string }> {
    const data = await apiFetch<{ message: string }>(`/api/topic/plans/${id}`, {
      method: 'DELETE',
    });
    return requireApiResult(data, '删除选题计划失败');
  },

  // === 选题创意 ===

  /**
   * 获取选题创意列表
   */
  async listIdeas(params?: IdeaListParams): Promise<{ items: TopicIdea[]; total: number; page: number; page_size: number }> {
    const query = new URLSearchParams();
    if (params?.plan_id) query.set('plan_id', String(params.plan_id));
    if (params?.status) query.set('status', params.status);
    if (params?.platform) query.set('platform', params.platform);
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    
    const data = await apiFetch<{ items: TopicIdea[]; total: number; page: number; page_size: number }>(`/api/topic/ideas?${query}`);
    return requireApiResult(data, '获取选题创意列表失败');
  },

  /**
   * 创建选题创意
   */
  async createIdea(data: CreateIdeaData): Promise<TopicIdea> {
    const result = await apiFetch<TopicIdea>('/api/topic/ideas', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return requireApiResult(result, '创建选题创意失败');
  },

  /**
   * 更新创意状态
   */
  async updateIdeaStatus(id: number, status: 'pending' | 'accepted' | 'rejected' | 'used'): Promise<TopicIdea> {
    const result = await apiFetch<TopicIdea>(`/api/topic/ideas/${id}/status?status=${status}`, {
      method: 'PUT',
    });
    return requireApiResult(result, '更新创意状态失败');
  },

  // === 热门话题 ===

  /**
   * 获取热门话题列表
   */
  async listHotTopics(params?: HotTopicListParams): Promise<{ items: HotTopic[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.platform) query.set('platform', params.platform);
    if (params?.category) query.set('category', params.category);
    if (params?.limit) query.set('limit', String(params.limit));
    
    const data = await apiFetch<{ items: HotTopic[]; total: number }>(`/api/topic/hot?${query}`);
    return requireApiResult(data, '获取热门话题列表失败');
  },

  /**
   * 发现热门话题
   */
  async discoverHotTopics(platform: string): Promise<{ discovered: HotTopic[]; count: number }> {
    const data = await apiFetch<{ discovered: HotTopic[]; count: number }>(`/api/topic/hot/discover?platform=${platform}`, {
      method: 'POST',
    });
    return requireApiResult(data, '发现热门话题失败');
  },

  /**
   * 获取单个热门话题
   */
  async getHotTopic(id: number): Promise<HotTopic> {
    const data = await apiFetch<HotTopic>(`/api/topic/hot/${id}`);
    return requireApiResult(data, '获取热门话题详情失败');
  },

  // === AI 推荐 ===

  /**
   * AI 选题推荐
   */
  async recommendTopics(params: RecommendParams): Promise<{ recommendations: TopicRecommendation[]; count: number }> {
    const query = new URLSearchParams();
    query.set('platform', params.platform);
    if (params.audience) query.set('audience', params.audience);
    if (params.count) query.set('count', String(params.count));
    
    const data = await apiFetch<{ recommendations: TopicRecommendation[]; count: number }>(`/api/topic/recommend?${query}`, {
      method: 'POST',
    });
    return requireApiResult(data, 'AI 选题推荐失败');
  },

  // === 排期日历 ===

  /**
   * 获取选题排期日历
   */
  async getCalendar(startDate: string, endDate: string): Promise<{ items: CalendarItem[]; start_date: string; end_date: string }> {
    const query = new URLSearchParams();
    query.set('start_date', startDate);
    query.set('end_date', endDate);
    
    const data = await apiFetch<{ items: CalendarItem[]; start_date: string; end_date: string }>(`/api/topic/calendar?${query}`);
    return requireApiResult(data, '获取排期日历失败');
  },
};

export default topicApi;
