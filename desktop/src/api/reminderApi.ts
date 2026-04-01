import type { ReminderConfig, ReminderConfigUpdate, PendingCustomer } from '../types';
import { apiFetch, requireApiResult } from '../lib/httpClient';

export const reminderApi = {
  /**
   * 获取提醒配置
   */
  async getConfig(): Promise<ReminderConfig> {
    const data = await apiFetch<ReminderConfig>('/api/reminder/config');
    return requireApiResult(data, '获取提醒配置失败');
  },

  /**
   * 更新提醒配置
   */
  async updateConfig(config: ReminderConfigUpdate): Promise<ReminderConfig> {
    const data = await apiFetch<ReminderConfig>('/api/reminder/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
    return requireApiResult(data, '更新提醒配置失败');
  },

  /**
   * 获取待跟进客户列表
   */
  async getPending(): Promise<PendingCustomer[]> {
    const data = await apiFetch<PendingCustomer[]>('/api/reminder/pending');
    return requireApiResult(data, '获取待跟进列表失败');
  },

  /**
   * 测试 Webhook
   */
  async testWebhook(): Promise<{ ok: boolean; result?: unknown }> {
    const data = await apiFetch<{ ok: boolean; result?: unknown }>('/api/reminder/test-webhook', {
      method: 'POST',
    });
    return requireApiResult(data, 'Webhook测试失败');
  },

  /**
   * 立即发送提醒
   */
  async sendNow(): Promise<{ ok: boolean; message: string }> {
    const data = await apiFetch<{ ok: boolean; message: string }>('/api/reminder/send-now', {
      method: 'POST',
    });
    return requireApiResult(data, '发送提醒失败');
  },
};

export default reminderApi;
