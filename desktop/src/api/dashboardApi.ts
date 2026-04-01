import type { BusinessMetrics, ConversionFunnel } from '../types';
import { apiFetch, requireApiResult } from '../lib/httpClient';

export const dashboardApi = {
  /**
   * 获取业务指标
   */
  async getMetrics(): Promise<BusinessMetrics> {
    const data = await apiFetch<BusinessMetrics>('/api/dashboard/metrics');
    return requireApiResult(data, '获取业务指标失败');
  },

  /**
   * 获取转化漏斗
   */
  async getFunnel(): Promise<ConversionFunnel> {
    const data = await apiFetch<ConversionFunnel>('/api/dashboard/funnel');
    return requireApiResult(data, '获取转化漏斗失败');
  },
};

export default dashboardApi;
