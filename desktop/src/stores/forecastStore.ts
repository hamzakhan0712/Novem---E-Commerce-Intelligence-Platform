import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type { ForecastResponse, ForecastMetric, MetricOverviewItem } from '@/types/forecasting';

interface ForecastState {
  metric: ForecastMetric;
  horizonDays: number;
  forecast: ForecastResponse | null;
  metricsOverview: MetricOverviewItem[];
  loading: boolean;
  error: string | null;

  setMetric: (m: ForecastMetric) => void;
  setHorizonDays: (d: number) => void;
  fetchForecast: (storeId: string) => Promise<void>;
  fetchMetricsOverview: (storeId: string) => Promise<void>;
  fetchAll: (storeId: string) => Promise<void>;
}

export const useForecastStore = create<ForecastState>()((set, get) => ({
  metric: 'revenue',
  horizonDays: 30,
  forecast: null,
  metricsOverview: [],
  loading: false,
  error: null,

  setMetric: (m) => set({ metric: m }),
  setHorizonDays: (d) => set({ horizonDays: d }),

  fetchForecast: async (storeId) => {
    const { metric, horizonDays } = get();
    const res = await apiClient.get<ApiResponse<ForecastResponse>>(
      `/forecasting?store_id=${encodeURIComponent(storeId)}&metric=${metric}&horizon_days=${horizonDays}`,
    );
    if (res.data.success && res.data.data) {
      set({ forecast: res.data.data });
    }
  },

  fetchMetricsOverview: async (storeId) => {
    const { horizonDays } = get();
    const res = await apiClient.get<ApiResponse<MetricOverviewItem[]>>(
      `/forecasting/metrics?store_id=${encodeURIComponent(storeId)}&horizon_days=${horizonDays}`,
    );
    if (res.data.success && res.data.data) {
      set({ metricsOverview: res.data.data });
    }
  },

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const results = await Promise.allSettled([
        get().fetchForecast(storeId),
        get().fetchMetricsOverview(storeId),
      ]);
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length === results.length) {
        set({ error: 'Failed to load forecast data' });
      }
    } catch {
      set({ error: 'Failed to load forecast data' });
    } finally {
      set({ loading: false });
    }
  },
}));
