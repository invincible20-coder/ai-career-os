import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  user: { id: string; email: string; name?: string; image?: string } | null;
  setAuth: (user: any) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  setAuth: (user) => set({ isAuthenticated: true, user }),
  clearAuth: () => set({ isAuthenticated: false, user: null }),
}));
