import { RawContentInboxItem, InboxListParams, InboxListResponse } from '../types';
import { apiFetch, requireApiResult } from '../lib/httpClient';
import { apiRoutes } from './routes';

// Mock 数据兜底
const MOCK_ITEMS: RawContentInboxItem[] = [
  {
    id: 1,
    platform: 'xiaohongshu',
    title: '小红书爆款笔记模板分享',
    content_preview: '今天给大家分享一个超好用的笔记模板，从标题到正文都有详细的写作技巧...',
    content: '今天给大家分享一个超好用的笔记模板，从标题到正文都有详细的写作技巧。首先是标题要抓人眼球，可以用数字开头或者提问式。其次是正文要有结构，分段清晰，最后加个总结。这套方法我已经用了三个月，效果非常好！',
    author_name: '内容达人',
    publish_time: '2026-03-28T10:00:00',
    url: 'https://example.com/1',
    like_count: 1200,
    comment_count: 89,
    favorite_count: 456,
    clean_status: 'cleaned',
    quality_status: 'good',
    risk_status: 'normal',
    quality_score: 82.5,
    risk_score: 5.0,
    material_status: 'not_in',
    created_at: '2026-03-28T10:00:00',
    source_id: 'xhs_001'
  },
  {
    id: 2,
    platform: 'douyin',
    title: '抖音短视频脚本创作指南',
    content_preview: '如何用3步写出一个爆款短视频脚本？第一步确定选题方向...',
    content: '如何用3步写出一个爆款短视频脚本？第一步确定选题方向，要选择热门话题或者用户痛点。第二步是脚本结构，开头3秒要抓住注意力，中间要有起伏，结尾要引导互动。第三步是优化，根据数据反馈不断调整。',
    author_name: '创作导师',
    publish_time: '2026-03-27T15:30:00',
    like_count: 3400,
    comment_count: 210,
    favorite_count: 890,
    clean_status: 'cleaned',
    quality_status: 'good',
    risk_status: 'normal',
    quality_score: 91.0,
    risk_score: 2.0,
    material_status: 'not_in',
    created_at: '2026-03-27T15:30:00'
  },
  {
    id: 3,
    platform: 'zhihu',
    title: '知乎高赞回答结构拆解',
    content_preview: '研究了100个高赞回答后发现这些共同规律：开头要直击痛点...',
    content: '研究了100个高赞回答后发现这些共同规律：开头要直击痛点，让读者产生共鸣。中间要有干货，用数据和案例支撑观点。结尾要有总结，并引导读者思考和互动。这套方法适用于大多数知识分享类问题。',
    author_name: '分析师小王',
    publish_time: '2026-03-26T09:00:00',
    like_count: 560,
    comment_count: 45,
    favorite_count: 120,
    clean_status: 'pending',
    quality_status: 'pending',
    risk_status: 'normal',
    quality_score: 0,
    risk_score: 0,
    material_status: 'not_in',
    created_at: '2026-03-26T09:00:00'
  },
  {
    id: 4,
    platform: 'weibo',
    title: '微博热门话题追踪技巧',
    content_preview: '做微博运营最重要的就是蹭热度，但要注意方式方法...',
    content: '做微博运营最重要的就是蹭热度，但要注意方式方法。首先要关注热搜榜，及时跟进热点。其次内容要和自己的领域相关，不要生搬硬套。最后要注意风险，避免触碰敏感话题。',
    author_name: '运营老李',
    publish_time: '2026-03-25T14:00:00',
    like_count: 200,
    comment_count: 30,
    favorite_count: 15,
    clean_status: 'cleaned',
    quality_status: 'low',
    risk_status: 'low_risk',
    quality_score: 35.5,
    risk_score: 32.0,
    material_status: 'ignored',
    created_at: '2026-03-25T14:00:00'
  },
  {
    id: 5,
    platform: 'wechat',
    title: '微信公众号爆款文章写作技巧',
    content_preview: '公众号文章想要10万+，这些技巧必须掌握...',
    content: '公众号文章想要10万+，这些技巧必须掌握。标题党要有度，吸引人但不能欺骗。开头要有钩子，让读者愿意继续往下看。排版要舒适，段落短小，图片精美。最后要有互动引导，鼓励读者转发和评论。',
    author_name: '新媒体专家',
    publish_time: '2026-03-24T11:00:00',
    like_count: 890,
    comment_count: 156,
    favorite_count: 234,
    clean_status: 'cleaned',
    quality_status: 'normal',
    risk_status: 'normal',
    quality_score: 68.0,
    risk_score: 8.5,
    material_status: 'in_material',
    created_at: '2026-03-24T11:00:00'
  }
];

export const inboxApi = {
  /**
   * 获取收件箱列表
   */
  async list(params: InboxListParams = {}): Promise<InboxListResponse> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '' && v !== null) {
        query.set(k, String(v));
      }
    });
    const data = await apiFetch<InboxListResponse>(`${apiRoutes.mvp.inbox}?${query}`);
    if (data && data.items) {
      return data;
    }
    // mock 兜底
    return { items: MOCK_ITEMS, total: MOCK_ITEMS.length, page: 1, size: 20 };
  },

  /**
   * 单条清洗
   */
  async clean(id: number): Promise<{ success: boolean; message?: string }> {
    const data = await apiFetch<{ success: boolean; message?: string }>(
      `${apiRoutes.mvp.inbox}/${id}/clean`,
      { method: 'POST' }
    );
    return requireApiResult(data, '清洗失败');
  },

  /**
   * 批量清洗
   */
  async batchClean(ids: number[]): Promise<{ success: boolean; total?: number }> {
    const data = await apiFetch<{ success: boolean; total?: number }>(
      `${apiRoutes.mvp.inbox}/batch-clean`,
      { method: 'POST', body: JSON.stringify({ ids }) }
    );
    return requireApiResult(data, '批量清洗失败');
  },

  /**
   * 单条质量筛选
   */
  async screen(id: number): Promise<{ success: boolean; message?: string }> {
    const data = await apiFetch<{ success: boolean; message?: string }>(
      `${apiRoutes.mvp.inbox}/${id}/screen`,
      { method: 'POST' }
    );
    return requireApiResult(data, '质量筛选失败');
  },

  /**
   * 批量质量筛选
   */
  async batchScreen(ids: number[]): Promise<{ success: boolean; total?: number }> {
    const data = await apiFetch<{ success: boolean; total?: number }>(
      `${apiRoutes.mvp.inbox}/batch-screen`,
      { method: 'POST', body: JSON.stringify({ ids }) }
    );
    return requireApiResult(data, '批量质量筛选失败');
  },

  /**
   * 单条入素材库
   */
  async toMaterial(id: number): Promise<{ success: boolean; message?: string }> {
    const data = await apiFetch<{ success: boolean; message?: string }>(
      `${apiRoutes.mvp.inbox}/${id}/to-material`,
      { method: 'POST' }
    );
    return requireApiResult(data, '入素材库失败');
  },

  /**
   * 批量入素材库
   */
  async batchToMaterial(ids: number[]): Promise<{ success: boolean; total?: number }> {
    const data = await apiFetch<{ success: boolean; total?: number }>(
      `${apiRoutes.mvp.inbox}/batch-to-material`,
      { method: 'POST', body: JSON.stringify({ ids }) }
    );
    return requireApiResult(data, '批量入素材库失败');
  },

  /**
   * 单条忽略
   */
  async ignore(id: number): Promise<{ success: boolean; message?: string }> {
    const data = await apiFetch<{ success: boolean; message?: string }>(
      `${apiRoutes.mvp.inbox}/${id}/ignore`,
      { method: 'POST' }
    );
    return requireApiResult(data, '忽略失败');
  },

  /**
   * 批量忽略
   */
  async batchIgnore(ids: number[]): Promise<{ success: boolean; total?: number }> {
    const data = await apiFetch<{ success: boolean; total?: number }>(
      `${apiRoutes.mvp.inbox}/batch-ignore`,
      { method: 'POST', body: JSON.stringify({ ids }) }
    );
    return requireApiResult(data, '批量忽略失败');
  },
};

export default inboxApi;
