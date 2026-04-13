import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import apiClient from '@/utils/apiClient';
import { setExchangeRate } from '@/utils/formatCurrency';
import type { ApiResponse } from '@/types/api';

type ThemeMode = 'dark' | 'light';

interface SettingsState {
  theme: ThemeMode;
  currency: string;
  exchangeRate: number;
  industryTemplate: 'general' | 'fashion';
  dateFormat: string;
  fiscalYearStart: number;
  zoomLevel: number;
  watchFolderPath: string | null;
  piiMaskingEnabled: boolean;
  region: string | null;
  churnThresholdDays: number;
  passwordPolicy: 'every_start' | 'once_per_session' | 'never';
  loading: boolean;
  error: string | null;

  fetchSettings: () => Promise<void>;
  fetchExchangeRate: (currency: string) => Promise<void>;
  updateSetting: (key: string, value: unknown) => Promise<void>;
  setTheme: (theme: ThemeMode) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'dark',
      currency: 'INR',
      exchangeRate: 1,
      industryTemplate: 'general',
      dateFormat: 'YYYY-MM-DD',
      fiscalYearStart: 1,
      zoomLevel: 100,
      watchFolderPath: null,
      piiMaskingEnabled: true,
      region: null,
      churnThresholdDays: 90,
      passwordPolicy: 'every_start',
      loading: false,
      error: null,

      fetchSettings: async () => {
        set({ loading: true, error: null });
        try {
          const res = await apiClient.get<ApiResponse<Record<string, string>>>(
            '/settings/preferences',
          );
          if (res.data.success && res.data.data) {
            const raw = res.data.data;
            const currency = raw.currency ?? 'INR';
            set((state) => ({
              ...state,
              theme: (raw.theme as ThemeMode) ?? state.theme,
              currency,
              industryTemplate: (raw.industry_template as 'general' | 'fashion') ?? state.industryTemplate,
              dateFormat: raw.date_format ?? state.dateFormat,
              fiscalYearStart: raw.fiscal_year_start ? Number(raw.fiscal_year_start) : state.fiscalYearStart,
              zoomLevel: raw.zoom_level ? Number(raw.zoom_level) : state.zoomLevel,
              watchFolderPath: raw.watch_folder_path ?? state.watchFolderPath,
              piiMaskingEnabled: raw.pii_masking_enabled !== undefined
                ? raw.pii_masking_enabled === 'true'
                : state.piiMaskingEnabled,
              region: raw.region ?? state.region,
              churnThresholdDays: raw.churn_threshold_days
                ? Number(raw.churn_threshold_days)
                : state.churnThresholdDays,
              passwordPolicy: (raw.password_policy as 'every_start' | 'once_per_session' | 'never') ?? state.passwordPolicy,
              loading: false,
            }));
            if (currency !== 'INR') {
              useSettingsStore.getState().fetchExchangeRate(currency);
            } else {
              setExchangeRate(1, 'INR');
            }
          } else {
            set({ loading: false });
          }
        } catch {
          set({ loading: false, error: 'Failed to load settings' });
        }
      },

      fetchExchangeRate: async (currency: string) => {
        if (currency === 'INR') {
          set({ exchangeRate: 1 });
          setExchangeRate(1, 'INR');
          return;
        }
        try {
          const res = await apiClient.get<ApiResponse<{ currency: string; rate: number }>>(
            `/settings/exchange-rate/${currency}`,
          );
          if (res.data.success && res.data.data) {
            const rate = res.data.data.rate;
            set({ exchangeRate: rate });
            setExchangeRate(rate, currency);
          }
        } catch {
          set({ exchangeRate: 1 });
          setExchangeRate(1, currency);
        }
      },

      updateSetting: async (key, value) => {
        try {
          await apiClient.put('/settings/preferences', {
            [key]: String(value),
          });
          set((state) => ({ ...state, [key]: value }));
          if (key === 'currency') {
            useSettingsStore.getState().fetchExchangeRate(String(value));
          }
        } catch {
          set({ error: `Failed to update ${key}` });
        }
      },

      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        set({ theme });
      },
    }),
    {
      name: 'novem-settings',
      partialize: (state) => ({
        theme: state.theme,
        currency: state.currency,
        dateFormat: state.dateFormat,
        zoomLevel: state.zoomLevel,
        piiMaskingEnabled: state.piiMaskingEnabled,
      }),
    },
  ),
);
