import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type {
  KpiData,
  TrendPoint,
  DashboardSummary,
  DashboardPeriod,
  DashboardMetric,
  DashboardGranularity,
  RevenueAtRisk,
} from '@/types/dashboard';

interface DashboardState {
  period: DashboardPeriod;
  metric: DashboardMetric;
  granularity: DashboardGranularity;
  kpis: KpiData | null;
  trends: TrendPoint[];
  revenueAtRisk: RevenueAtRisk | null;
  loading: boolean;
  error: string | null;

  setPeriod: (p: DashboardPeriod) => void;
  setMetric: (m: DashboardMetric) => void;
  setGranularity: (g: DashboardGranularity) => void;
  fetchSummary: (storeId: string) => Promise<void>;
  fetchTrends: (storeId: string) => Promise<void>;
  fetchRevenueAtRisk: (storeId: string) => Promise<void>;
}

export const useDashboardStore = create<DashboardState>()((set, get) => ({
  period: '30d',
  metric: 'revenue',
  granularity: 'daily',
  kpis: null,
  trends: [],
  revenueAtRisk: null,
  loading: false,
  error: null,

  setPeriod: (p) => set({ period: p }),
  setMetric: (m) => set({ metric: m }),
  setGranularity: (g) => set({ granularity: g }),

  fetchSummary: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const { period } = get();
      const res = await apiClient.get<ApiResponse<DashboardSummary>>(
        `/dashboard/summary?store_id=${encodeURIComponent(storeId)}&period=${period}`,
      );
      if (res.data.success && res.data.data) {
        set({
          kpis: res.data.data.kpis,
          trends: res.data.data.trends ?? [],
        });
      }
    } catch {
      set({ error: 'Failed to load dashboard data' });
    } finally {
      set({ loading: false });
    }
  },

  fetchTrends: async (storeId) => {
    try {
      const { metric, granularity, period } = get();
      const res = await apiClient.get<ApiResponse<TrendPoint[]>>(
        `/dashboard/trends?store_id=${encodeURIComponent(storeId)}&metric=${metric}&granularity=${granularity}&period=${period}`,
      );
      if (res.data.success && res.data.data) {
        set({ trends: res.data.data });
      }
    } catch {
      // trends fetch failure is non-critical
    }
  },

  fetchRevenueAtRisk: async (storeId) => {
    try {
      const { period } = get();
      const res = await apiClient.get<ApiResponse<RevenueAtRisk>>(
        `/dashboard/revenue-at-risk?store_id=${encodeURIComponent(storeId)}&period=${period}`,
      );
      if (res.data.success && res.data.data) {
        set({ revenueAtRisk: res.data.data });
      }
    } catch {
      // non-critical
    }
  },
}));
