import type {
  ConversationItem,
  MessageItem,
  ReplyRequest,
  SuggestRequest,
  SuggestResponse,
} from '../types';
import { apiFetch, requireApiResult } from '../lib/httpClient';

export const conversationApi = {
  /**
   * 获取会话列表
   */
  async list(): Promise<ConversationItem[]> {
    const data = await apiFetch<ConversationItem[]>('/api/conversations');
    return requireApiResult(data, '获取会话列表失败');
  },

  /**
   * 获取会话详情
   */
  async getDetail(conversationId: number): Promise<ConversationItem> {
    const data = await apiFetch<ConversationItem>(`/api/conversations/${conversationId}`);
    return requireApiResult(data, '获取会话详情失败');
  },

  /**
   * 获取会话消息列表
   */
  async getMessages(conversationId: number): Promise<MessageItem[]> {
    const data = await apiFetch<MessageItem[]>(`/api/conversations/${conversationId}/messages`);
    return requireApiResult(data, '获取消息列表失败');
  },

  /**
   * 发送回复
   */
  async reply(conversationId: number, request: ReplyRequest): Promise<MessageItem> {
    const data = await apiFetch<MessageItem>(`/api/conversations/${conversationId}/reply`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '发送回复失败');
  },

  /**
   * 获取回复建议
   */
  async suggest(request: SuggestRequest): Promise<SuggestResponse> {
    const data = await apiFetch<SuggestResponse>('/api/conversations/suggest', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return requireApiResult(data, '获取回复建议失败');
  },

  /**
   * 人工接管会话
   */
  async takeover(conversationId: number): Promise<{ ok: boolean; message: string }> {
    const data = await apiFetch<{ ok: boolean; message: string }>(`/api/conversations/${conversationId}/takeover`, {
      method: 'POST',
    });
    return requireApiResult(data, '接管会话失败');
  },
};

export default conversationApi;
