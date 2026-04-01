import type { TrafficStrategy, TrafficStrategySummary } from '../types';
import { apiFetch, requireApiResult } from '../lib/httpClient';

// 列表响应类型
interface ListStrategiesResponse {
  total: number;
  items: TrafficStrategy[];
  page: number;
  page_size: number;
}

export const trafficApi = {
  /**
   * 获取策略列表
   */
  async listStrategies(params?: {
    platform?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<ListStrategiesResponse> {
    const queryParams = new URLSearchParams();
    if (params?.platform) queryParams.append('platform', params.platform);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const data = await apiFetch<ListStrategiesResponse>(`/api/traffic/strategies${query}`);
    return requireApiResult(data, '获取策略列表失败');
  },

  /**
   * 获取单个策略详情
   */
  async getStrategy(strategyId: number): Promise<TrafficStrategy> {
    const data = await apiFetch<TrafficStrategy>(`/api/traffic/strategies/${strategyId}`);
    return requireApiResult(data, '获取策略详情失败');
  },

  /**
   * 创建策略
   */
  async createStrategy(strategyData: Partial<TrafficStrategy>): Promise<TrafficStrategy> {
    const data = await apiFetch<TrafficStrategy>('/api/traffic/strategies', {
      method: 'POST',
      body: JSON.stringify(strategyData),
    });
    return requireApiResult(data, '创建策略失败');
  },

  /**
   * 更新策略
   */
  async updateStrategy(strategyId: number, strategyData: Partial<TrafficStrategy>): Promise<TrafficStrategy> {
    const data = await apiFetch<TrafficStrategy>(`/api/traffic/strategies/${strategyId}`, {
      method: 'PUT',
      body: JSON.stringify(strategyData),
    });
    return requireApiResult(data, '更新策略失败');
  },

  /**
   * 删除策略
   */
  async deleteStrategy(strategyId: number): Promise<{ message: string }> {
    const data = await apiFetch<{ message: string }>(`/api/traffic/strategies/${strategyId}`, {
      method: 'DELETE',
    });
    return requireApiResult(data, '删除策略失败');
  },

  /**
   * 更新策略效果指标
   */
  async updateMetrics(strategyId: number, metrics: {
    views?: number;
    clicks?: number;
    leads?: number;
    conversions?: number;
    cost_per_lead?: number;
  }): Promise<TrafficStrategy> {
    const data = await apiFetch<TrafficStrategy>(`/api/traffic/strategies/${strategyId}/metrics`, {
      method: 'PUT',
      body: JSON.stringify({ metrics }),
    });
    return requireApiResult(data, '更新指标失败');
  },

  /**
   * 获取引流效果汇总
   */
  async getSummary(): Promise<TrafficStrategySummary> {
    const data = await apiFetch<TrafficStrategySummary>('/api/traffic/summary');
    return requireApiResult(data, '获取汇总数据失败');
  },
};

export default trafficApi;
