import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  username: string;
  role: string;
  [key: string]: any;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
}

// 旧的localStorage key名称（用于数据迁移）
const OLD_TOKEN_KEY = 'zhk_token';

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token: string, user: User) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
      setToken: (token: string) => set({ token, isAuthenticated: true }),
      setUser: (user: User) => set({ user }),
    }),
    {
      name: 'zhk-auth', // localStorage key
      partialize: (state) => ({ 
        token: state.token, 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);

// 数据迁移：将旧的localStorage数据迁移到新的store
export const migrateOldAuth = (): void => {
  if (typeof window === 'undefined') return;
  
  const oldToken = localStorage.getItem(OLD_TOKEN_KEY);
  const currentState = useAuthStore.getState();
  
  // 如果存在旧token且store中没有token，则迁移
  if (oldToken && !currentState.token) {
    currentState.setToken(oldToken);
    // 可选：迁移后清除旧key（保留以保持向后兼容）
    // localStorage.removeItem(OLD_TOKEN_KEY);
  }
};

// 在模块加载时自动执行迁移
migrateOldAuth();
