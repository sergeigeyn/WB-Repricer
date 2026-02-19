import { create } from 'zustand';
import apiClient from '@/api/client';
import { getToken, setTokens, removeTokens } from '@/utils/token';

interface AuthState {
  isAuthenticated: boolean;
  user: { id: number; email: string; name: string; role: string } | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!getToken(),
  user: null,

  login: async (email: string, password: string) => {
    const { data } = await apiClient.post('/auth/login', { email, password });
    setTokens(data.access_token, data.refresh_token);
    set({ isAuthenticated: true });
  },

  logout: () => {
    removeTokens();
    set({ isAuthenticated: false, user: null });
  },
}));
