import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from '../../pages/LoginPage';

// Mock API and auth
vi.mock('../../lib/api', () => ({
  login: vi.fn(),
}));

vi.mock('../../lib/auth', () => ({
  setToken: vi.fn(),
  consumeRedirectPath: vi.fn().mockReturnValue('/dashboard'),
}));

vi.mock('../../store', () => ({
  useAuthStore: {
    getState: vi.fn().mockReturnValue({
      token: null,
      isAuthenticated: false,
      user: null,
      setToken: vi.fn(),
      setUser: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
    }),
  },
  migrateOldAuth: vi.fn(),
}));

import { login } from '../../lib/api';
import { setToken } from '../../lib/auth';

describe('AuthFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { pathname: '/login' },
      writable: true
    });
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {component}
      </BrowserRouter>
    );
  };

  it('应正确渲染登录页面', async () => {
    renderWithRouter(<LoginPage />);

    expect(await screen.findByText('欢迎进入智获客')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
  });

  it('应显示默认用户名和密码', async () => {
    renderWithRouter(<LoginPage />);

    await screen.findByText('欢迎进入智获客');
    const inputs = screen.getAllByRole('textbox');
    const passwordInput = screen.getByDisplayValue('password123') as HTMLInputElement;

    expect(inputs[0]).toHaveValue('testuser');
    expect(passwordInput).toHaveValue('password123');
  });

  it('应支持输入用户名和密码', async () => {
    renderWithRouter(<LoginPage />);

    await screen.findByText('欢迎进入智获客');
    const inputs = screen.getAllByRole('textbox');
    const usernameInput = inputs[0];

    fireEvent.change(usernameInput, { target: { value: 'newuser' } });

    expect(usernameInput).toHaveValue('newuser');
  });

  it('登录成功应调用API并存储token', async () => {
    const mockToken = 'mock_access_token_123';
    vi.mocked(login).mockResolvedValue({ access_token: mockToken });

    renderWithRouter(<LoginPage />);
    
    const loginButton = screen.getByRole('button', { name: '登录' });
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(login).toHaveBeenCalledWith('testuser', 'password123');
      expect(setToken).toHaveBeenCalledWith(mockToken);
    });
  });

  it('登录失败应显示错误信息', async () => {
    vi.mocked(login).mockRejectedValue({
      response: { data: { detail: '用户名或密码错误' } }
    });

    renderWithRouter(<LoginPage />);
    
    const loginButton = screen.getByRole('button', { name: '登录' });
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(screen.getByText('用户名或密码错误')).toBeInTheDocument();
    });
  });

  it('登录时应显示加载状态', async () => {
    vi.mocked(login).mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<LoginPage />);
    
    const loginButton = screen.getByRole('button', { name: '登录' });
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(screen.getByText('登录中...')).toBeInTheDocument();
    });
  });

  it('应显示登录说明文字', async () => {
    renderWithRouter(<LoginPage />);

    expect(await screen.findByText(/先登录，再开始采集、改写、审核和客户跟进/)).toBeInTheDocument();
  });
});
