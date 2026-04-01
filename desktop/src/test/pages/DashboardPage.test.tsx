import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { DashboardPage } from '../../pages/DashboardPage';

// Mock recharts
vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line">Line</div>,
  XAxis: () => <div>XAxis</div>,
  YAxis: () => <div>YAxis</div>,
  Tooltip: () => <div>Tooltip</div>,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
}));

// Mock API calls
vi.mock('../../lib/api', () => ({
  getDashboardSummary: vi.fn(),
  getTrend: vi.fn(),
  getLeadFunnel: vi.fn(),
}));

import { getDashboardSummary, getTrend, getLeadFunnel } from '../../lib/api';

const mockSummary = {
  today_new_customers: 5,
  today_wechat_adds: 12,
  today_leads: 23,
  today_valid_leads: 18,
  today_conversions: 3,
  pending_follow_count: 8,
  pending_review_count: 4
};

const mockTrend = {
  data: [
    { date: '2026-03-25', total_leads: 15, total_valid_leads: 12 },
    { date: '2026-03-26', total_leads: 20, total_valid_leads: 16 },
    { date: '2026-03-27', total_leads: 18, total_valid_leads: 14 },
  ]
};

const mockFunnel = {
  stages: [
    { stage: 'published', stage_label: '已发布', count: 100, rate: 1.0 },
    { stage: 'leads_generated', stage_label: '线索产生', count: 80, rate: 0.8 },
    { stage: 'contacted', stage_label: '已联系', count: 60, rate: 0.6 },
    { stage: 'qualified', stage_label: '已合格', count: 40, rate: 0.4 },
    { stage: 'converted', stage_label: '已转化', count: 20, rate: 0.2 },
  ],
  period_days: 30
};

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {component}
      </BrowserRouter>
    );
  };

  it('应正确渲染页面标题', async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(mockSummary);
    vi.mocked(getTrend).mockResolvedValue(mockTrend);
    vi.mocked(getLeadFunnel).mockResolvedValue(mockFunnel);

    renderWithRouter(<DashboardPage />);

    expect(await screen.findByText('经营看板')).toBeInTheDocument();
  });

  it('加载状态应显示loading', () => {
    vi.mocked(getDashboardSummary).mockImplementation(() => new Promise(() => {}));
    vi.mocked(getTrend).mockImplementation(() => new Promise(() => {}));
    vi.mocked(getLeadFunnel).mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<DashboardPage />);
    
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('应正确显示数据卡片', async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(mockSummary);
    vi.mocked(getTrend).mockResolvedValue(mockTrend);
    vi.mocked(getLeadFunnel).mockResolvedValue(mockFunnel);

    renderWithRouter(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText('今日新增客户')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('今日加微数')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
      expect(screen.getByText('今日线索数')).toBeInTheDocument();
      expect(screen.getByText('23')).toBeInTheDocument();
    });
  });

  it('应渲染图表区域', async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(mockSummary);
    vi.mocked(getTrend).mockResolvedValue(mockTrend);
    vi.mocked(getLeadFunnel).mockResolvedValue(mockFunnel);

    renderWithRouter(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText('最近7天线索趋势')).toBeInTheDocument();
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    });
  });

  it('应渲染转化漏斗', async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue(mockSummary);
    vi.mocked(getTrend).mockResolvedValue(mockTrend);
    vi.mocked(getLeadFunnel).mockResolvedValue(mockFunnel);

    renderWithRouter(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/转化漏斗/)).toBeInTheDocument();
      expect(screen.getByText('已发布')).toBeInTheDocument();
      expect(screen.getByText('已转化')).toBeInTheDocument();
    });
  });
});
