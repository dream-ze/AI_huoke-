import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MvpMaterialsPage from '../../pages/materials/MvpMaterialsPage';

// Mock API
vi.mock('../../lib/api', () => ({
  mvpListMaterials: vi.fn(),
  mvpGetMaterial: vi.fn(),
  mvpBuildKnowledge: vi.fn(),
  mvpBatchBuildKnowledge: vi.fn(),
  mvpToggleMaterialHot: vi.fn(),
  mvpUpdateTags: vi.fn(),
  mvpListTags: vi.fn(),
}));

import { 
  mvpListMaterials, 
  mvpListTags 
} from '../../lib/api';

const mockMaterials = [
  {
    id: 1,
    title: '测试素材1',
    platform: 'xiaohongshu',
    content: '测试内容1',
    author: '作者1',
    source_url: 'https://example.com/1',
    like_count: 100,
    comment_count: 20,
    is_hot: true,
    use_count: 5,
    risk_level: 'low',
    tags: [{ id: 1, name: '标签1', type: 'topic' }],
    created_at: '2026-03-28T10:00:00'
  },
  {
    id: 2,
    title: '测试素材2',
    platform: 'douyin',
    content: '测试内容2',
    author: '作者2',
    source_url: 'https://example.com/2',
    like_count: 200,
    comment_count: 40,
    is_hot: false,
    use_count: 3,
    risk_level: 'medium',
    tags: [{ id: 2, name: '标签2', type: 'audience' }],
    created_at: '2026-03-27T15:30:00'
  }
];

const mockTags = [
  { id: 1, name: '标签1', type: 'topic' },
  { id: 2, name: '标签2', type: 'audience' },
  { id: 3, name: '标签3', type: 'style' }
];

describe('MvpMaterialsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(mvpListMaterials).mockResolvedValue({
      items: mockMaterials,
      total: mockMaterials.length
    });
    vi.mocked(mvpListTags).mockResolvedValue(mockTags);
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {component}
      </BrowserRouter>
    );
  };

  it('应正确渲染页面标题', async () => {
    renderWithRouter(<MvpMaterialsPage />);

    expect(await screen.findByText('素材库 - 素材资产池')).toBeInTheDocument();
  });

  it('应显示筛选器', async () => {
    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
    });
  });

  it('应加载并显示素材列表', async () => {
    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      expect(screen.getByText('测试素材1')).toBeInTheDocument();
      expect(screen.getByText('测试素材2')).toBeInTheDocument();
    });
  });

  it('应显示空状态当素材库为空', async () => {
    vi.mocked(mvpListMaterials).mockResolvedValue([]);

    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      expect(screen.getByText('素材库为空')).toBeInTheDocument();
      expect(screen.getByText('请先从收件箱将内容入库')).toBeInTheDocument();
    });
  });

  it('应显示搜索框', async () => {
    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('搜索标题或内容...');
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('应显示表格列标题', async () => {
    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      expect(screen.getByText('标题')).toBeInTheDocument();
      expect(screen.getByText('平台')).toBeInTheDocument();
      expect(screen.getByText('标签')).toBeInTheDocument();
      expect(screen.getByText('爆款')).toBeInTheDocument();
    });
  });

  it('应显示详情区域提示', async () => {
    renderWithRouter(<MvpMaterialsPage />);
    
    await waitFor(() => {
      expect(screen.getByText('请选择一条素材查看详情')).toBeInTheDocument();
    });
  });
});
