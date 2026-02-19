import { create } from 'zustand';
import apiClient from '@/api/client';
import { getToken, setTokens, removeTokens } from '@/utils/token';

interface UserInfo {
  id: number;
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: UserInfo | null;
  login: (email: string, password: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!getToken(),
  user: null,

  login: async (email: string, password: string) => {
    const { data } = await apiClient.post('/auth/login', { email, password });
    setTokens(data.access_token, data.refresh_token);
    set({ isAuthenticated: true });

    // Fetch user profile after login
    try {
      const { data: user } = await apiClient.get('/auth/me');
      set({ user });
    } catch {
      // Token works but /me failed — still authenticated
    }
  },

  fetchUser: async () => {
    try {
      const { data: user } = await apiClient.get('/auth/me');
      set({ user, isAuthenticated: true });
    } catch {
      removeTokens();
      set({ isAuthenticated: false, user: null });
    }
  },

  logout: () => {
    removeTokens();
    set({ isAuthenticated: false, user: null });
  },
}));
