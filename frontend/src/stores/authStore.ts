import { create } from 'zustand';
import type { UserOut } from '@/types/api';

interface AuthState {
  user: UserOut | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuth: (user: UserOut, token: string) => void;
  setUser: (user: UserOut) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('bb_token'),
  isAuthenticated: !!localStorage.getItem('bb_token'),
  isLoading: true,

  setAuth: (user, token) => {
    localStorage.setItem('bb_token', token);
    set({ user, token, isAuthenticated: true, isLoading: false });
  },

  setUser: (user) => {
    set({ user, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem('bb_token');
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  initialize: () => {
    const token = localStorage.getItem('bb_token');
    set({ token, isAuthenticated: !!token, isLoading: !!token });
  },
}));
