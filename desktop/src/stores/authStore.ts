import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type { AuthStatus, LoginResponse, SetupRequest, UserProfile } from '@/types/auth';

const TOKEN_KEY = 'novem-session-token';
const SESSION_AUTH_KEY = 'novem-session-auth';

type PasswordPolicy = 'every_start' | 'once_per_session' | 'never';

interface AuthState {
  isSetupComplete: boolean | null;
  isAuthenticated: boolean;
  isLocked: boolean;
  user: UserProfile | null;
  token: string | null;
  passwordPolicy: PasswordPolicy;
  loading: boolean;
  error: string | null;

  checkStatus: () => Promise<void>;
  setup: (req: SetupRequest) => Promise<LoginResponse>;
  setAuth: (token: string, user: UserProfile) => void;
  login: (password: string) => Promise<void>;
  autoLogin: () => Promise<void>;
  lock: () => Promise<void>;
  updateProfile: (fields: Partial<UserProfile>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  getSecurityQuestion: () => Promise<string | null>;
  forgotPassword: (securityAnswer: string) => Promise<string>;
  resetPassword: (resetToken: string, newPassword: string) => Promise<void>;
  setPasswordPolicy: (policy: PasswordPolicy) => void;
  clearError: () => void;
}

function setToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    delete apiClient.defaults.headers.common['Authorization'];
  }
}

function restoreToken(): string | null {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
  return token;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  isSetupComplete: null,
  isAuthenticated: false,
  isLocked: false,
  user: null,
  token: restoreToken(),
  passwordPolicy: 'every_start',
  loading: false,
  error: null,

  checkStatus: async () => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.get<ApiResponse<AuthStatus>>('/auth/status');
      const data = res.data.data;
      const isSetupComplete = data?.is_setup_complete ?? false;
      const user = data?.user ?? null;
      const passwordPolicy: PasswordPolicy = data?.password_policy ?? 'every_start';

      if (!isSetupComplete) {
        setToken(null);
        set({ isSetupComplete: false, isAuthenticated: false, user: null, loading: false, passwordPolicy });
        return;
      }

      const storedToken = get().token;

      // For all policies: if a stored token exists, verify it server-side.
      // This handles page refreshes robustly — sessionStorage can be unreliable
      // in Tauri WebView2, so we rely on the actual session in SQLite.
      // "every_start" semantics are enforced by clearing sessions on engine startup.
      if (storedToken) {
        try {
          const verifyRes = await apiClient.post<ApiResponse<{ valid: boolean }>>(
            `/auth/verify?token=${storedToken}`,
          );
          if (verifyRes.data.data?.valid) {
            sessionStorage.setItem(SESSION_AUTH_KEY, 'true');
            set({ isSetupComplete: true, isAuthenticated: true, user, loading: false, passwordPolicy });
            return;
          }
        } catch {
          // Verification request failed — fall through to unauthenticated
        }
      }

      // No valid token — clear and require login (or trigger autoLogin for 'never')
      setToken(null);
      set({ isSetupComplete: true, isAuthenticated: false, user, loading: false, passwordPolicy });
    } catch {
      set({ loading: false, error: 'Unable to connect to the engine' });
    }
  },

  setup: async (req) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<LoginResponse>>('/auth/setup', req);
      if (res.data.success && res.data.data) {
        const { token, user } = res.data.data;
        setToken(token);
        set({ loading: false });
        return { token, user };
      }
      throw new Error('Setup failed');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Setup failed';
      set({ loading: false, error: msg });
      throw err;
    }
  },

  setAuth: (token, user) => {
    setToken(token);
    set({ isSetupComplete: true, isAuthenticated: true, user, token, loading: false });
  },

  login: async (password) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<LoginResponse>>('/auth/login', { password });
      if (res.data.success && res.data.data) {
        const { token, user } = res.data.data;
        setToken(token);
        sessionStorage.setItem(SESSION_AUTH_KEY, 'true');
        set({ isAuthenticated: true, isLocked: false, user, token, loading: false });
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Incorrect password';
      set({ loading: false, error: msg });
    }
  },

  autoLogin: async () => {
    try {
      const res = await apiClient.post<ApiResponse<LoginResponse>>('/auth/auto-login');
      if (res.data.success && res.data.data) {
        const { token, user } = res.data.data;
        setToken(token);
        set({ isAuthenticated: true, isLocked: false, user, token });
      }
    } catch {
      // auto-login failed — user will see login screen
    }
  },

  lock: async () => {
    try {
      await apiClient.post('/auth/lock');
    } catch {
      // lock even if the request fails
    }
    setToken(null);
    sessionStorage.removeItem(SESSION_AUTH_KEY);
    set({ isAuthenticated: false, isLocked: true, token: null });
  },

  updateProfile: async (fields) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.patch<ApiResponse<UserProfile>>('/auth/profile', fields);
      if (res.data.success && res.data.data) {
        set({ user: res.data.data, loading: false });
      }
    } catch {
      set({ loading: false, error: 'Failed to update profile' });
    }
  },

  changePassword: async (currentPassword, newPassword) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<{ token: string }>>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      if (res.data.success && res.data.data) {
        setToken(res.data.data.token);
        set({ token: res.data.data.token, loading: false });
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to change password';
      set({ loading: false, error: msg });
    }
  },

  getSecurityQuestion: async () => {
    try {
      const res = await apiClient.get<ApiResponse<{ security_question: string }>>('/auth/security-question');
      return res.data.data?.security_question ?? null;
    } catch {
      return null;
    }
  },

  forgotPassword: async (securityAnswer) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<{ reset_token: string }>>('/auth/forgot-password', {
        security_answer: securityAnswer,
      });
      if (res.data.success && res.data.data) {
        set({ loading: false });
        return res.data.data.reset_token;
      }
      throw new Error('Failed');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Incorrect answer';
      set({ loading: false, error: msg });
      throw err;
    }
  },

  resetPassword: async (resetToken, newPassword) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<{ token: string }>>('/auth/reset-password', {
        reset_token: resetToken,
        new_password: newPassword,
      });
      if (res.data.success && res.data.data) {
        setToken(res.data.data.token);
        sessionStorage.setItem(SESSION_AUTH_KEY, 'true');
        set({ token: res.data.data.token, isAuthenticated: true, isLocked: false, loading: false });
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to reset password';
      set({ loading: false, error: msg });
      throw err;
    }
  },

  setPasswordPolicy: (policy) => set({ passwordPolicy: policy }),

  clearError: () => set({ error: null }),
}));
