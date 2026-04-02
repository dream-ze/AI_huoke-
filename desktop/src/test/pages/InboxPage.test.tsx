import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MvpInboxPage from '../../pages/inbox/MvpInboxPage';

// Mock API
vi.mock('../../api/inboxApi', () => ({
  inboxApi: {
    list: vi.fn(),
    clean: vi.fn(),
    screen: vi.fn(),
    toMaterial: vi.fn(),
    ignore: vi.fn(),
    batchClean: vi.fn(),
    batchScreen: vi.fn(),
    batchToMaterial: vi.fn(),
    batchIgnore: vi.fn(),
  }
}));

import { inboxApi } from '../../api/inboxApi';

const mockItems = [
  {
    id: 1,
    platform: 'xiaohongshu',
    title: '测试标题1',
    content_preview: '测试内容预览1',
    content: '测试内容1',
    author_name: '作者1',
    publish_time: '2026-03-28T10:00:00',
    like_count: 100,
    comment_count: 20,
    favorite_count: 30,
    clean_status: 'cleaned' as const,
    quality_status: 'good' as const,
    risk_status: 'normal' as const,
    material_status: 'not_in' as const,
    quality_score: 85.5,
    risk_score: 5.0,
    created_at: '2026-03-28T10:00:00',
    source_id: 'xhs_001'
  },
  {
    id: 2,
    platform: 'douyin',
    title: '测试标题2',
    content_preview: '测试内容预览2',
    content: '测试内容2',
    author_name: '作者2',
    publish_time: '2026-03-27T15:30:00',
    like_count: 200,
    comment_count: 40,
    favorite_count: 60,
    clean_status: 'pending' as const,
    quality_status: 'pending' as const,
    risk_status: 'normal' as const,
    material_status: 'not_in' as const,
    quality_score: 0,
    risk_score: 0,
    created_at: '2026-03-27T15:30:00',
    source_id: 'dy_001'
  }
];

describe('MvpInboxPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(inboxApi.list).mockResolvedValue({
      items: mockItems,
      total: mockItems.length,
      page: 1,
      size: 20
    });
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {component}
      </BrowserRouter>
    );
  };

  it('应正确渲染页面标题', async () => {
    renderWithRouter(<MvpInboxPage />);

    expect(await screen.findByText('原始内容池（收件箱）')).toBeInTheDocument();
  });

  it('应显示筛选器', async () => {
    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      expect(screen.getByText('全部平台')).toBeInTheDocument();
      expect(screen.getByText('全部清洗')).toBeInTheDocument();
      expect(screen.getByText('全部质量')).toBeInTheDocument();
    });
  });

  it('应加载并显示列表数据', async () => {
    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      expect(screen.getByText('测试标题1')).toBeInTheDocument();
      expect(screen.getByText('测试标题2')).toBeInTheDocument();
    });
  });

  it('应显示空状态当没有数据', async () => {
    vi.mocked(inboxApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      size: 20
    });

    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      expect(screen.getByText('暂无收件箱内容')).toBeInTheDocument();
      expect(screen.getByText('请前往采集中心导入内容')).toBeInTheDocument();
    });
  });

  it('应支持搜索功能', async () => {
    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('关键词搜索...');
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('应显示批量操作按钮', async () => {
    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      expect(screen.getByText('批量清洗')).toBeInTheDocument();
      expect(screen.getByText('批量质量筛选')).toBeInTheDocument();
      expect(screen.getByText('批量入素材库')).toBeInTheDocument();
      expect(screen.getByText('批量忽略')).toBeInTheDocument();
    });
  });

  it('应显示分页控件', async () => {
    renderWithRouter(<MvpInboxPage />);
    
    await waitFor(() => {
      expect(screen.getByText('上一页')).toBeInTheDocument();
      expect(screen.getByText('下一页')).toBeInTheDocument();
    });
  });
});
