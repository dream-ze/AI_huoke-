// 合规审核 API 模块
// 对接 /api/compliance/* 所有端点
import { apiFetch, requireApiResult } from '../lib/httpClient';

// 类型定义
export interface ComplianceCheckResult {
  is_compliant: boolean;
  risk_level: 'low' | 'medium' | 'high';
  violations?: Array<{
    type: string;
    message: string;
    position?: { start: number; end: number };
    suggestion?: string;
  }>;
  suggestions?: string[];
  checked_at: string;
}

export interface ComplianceCheckRequest {
  content: string;
  content_type?: 'post' | 'comment' | 'message' | 'profile';
}

export const complianceApi = {
  /**
   * 检查内容合规性
   */
  async check(request: ComplianceCheckRequest): Promise<ComplianceCheckResult> {
    const data = await apiFetch<ComplianceCheckResult>('/api/compliance/check', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '合规检查失败');
  },

  /**
   * 快速检查内容合规性（简化版）
   */
  async checkContent(content: string, contentType: 'post' | 'comment' | 'message' | 'profile' = 'post'): Promise<ComplianceCheckResult> {
    return this.check({ content, content_type: contentType });
  },
};

export default complianceApi;
