import type { BusinessMetrics, ConversionFunnel, ContentLayerMetrics, AcquisitionLayerMetrics, ConversionLayerMetrics, ThreeLayerDashboard } from '../types';
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

  /**
   * 获取内容层指标
   */
  async getContentLayerMetrics(period: string = 'today'): Promise<ContentLayerMetrics> {
    const data = await apiFetch<ContentLayerMetrics>(`/api/dashboard/content-metrics?period=${period}`);
    return requireApiResult(data, '获取内容层指标失败');
  },

  /**
   * 获取获客层指标
   */
  async getAcquisitionLayerMetrics(period: string = 'week'): Promise<AcquisitionLayerMetrics> {
    const data = await apiFetch<AcquisitionLayerMetrics>(`/api/dashboard/acquisition-metrics?period=${period}`);
    return requireApiResult(data, '获取获客层指标失败');
  },

  /**
   * 获取转化层指标
   */
  async getConversionLayerMetrics(period: string = 'month'): Promise<ConversionLayerMetrics> {
    const data = await apiFetch<ConversionLayerMetrics>(`/api/dashboard/conversion-metrics?period=${period}`);
    return requireApiResult(data, '获取转化层指标失败');
  },

  /**
   * 获取三层看板汇总
   */
  async getThreeLayerDashboard(period: string = 'week'): Promise<ThreeLayerDashboard> {
    const data = await apiFetch<ThreeLayerDashboard>(`/api/dashboard/three-layer?period=${period}`);
    return requireApiResult(data, '获取三层看板失败');
  },
};

export default dashboardApi;
