import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type {
  Insight, Anomaly, RecommendedAction, InsightSummary, InsightPeriod,
  CausalBreakdown, MissedRevenueSummary, FeedItem, BusinessHealthScore,
  ShapExplanation, ScenarioResult, BusinessDna, RootCauseNarrative,
} from '@/types/insights';

interface InsightState {
  period: InsightPeriod;
  insights: Insight[];
  anomalies: Anomaly[];
  actions: RecommendedAction[];
  summary: InsightSummary | null;
  drivers: CausalBreakdown | null;
  missedRevenue: MissedRevenueSummary | null;
  feed: FeedItem[];
  healthScore: BusinessHealthScore | null;
  shap: ShapExplanation | null;
  scenario: ScenarioResult | null;
  businessDna: BusinessDna | null;
  rootCause: RootCauseNarrative | null;
  loading: boolean;
  error: string | null;

  setPeriod: (period: InsightPeriod) => void;
  fetchInsights: (storeId: string) => Promise<void>;
  fetchAnomalies: (storeId: string) => Promise<void>;
  fetchActions: (storeId: string) => Promise<void>;
  fetchSummary: (storeId: string) => Promise<void>;
  fetchDrivers: (storeId: string, metric?: string) => Promise<void>;
  fetchMissedRevenue: (storeId: string) => Promise<void>;
  fetchFeed: (storeId: string) => Promise<void>;
  fetchHealthScore: (storeId: string) => Promise<void>;
  fetchShap: (storeId: string) => Promise<void>;
  runScenario: (storeId: string, adjustments: Record<string, number>) => Promise<void>;
  fetchBusinessDna: (storeId: string) => Promise<void>;
  fetchRootCause: (storeId: string) => Promise<void>;
  fetchAll: (storeId: string) => Promise<void>;
}

export const useInsightStore = create<InsightState>()((set, get) => ({
  period: '30d',
  insights: [],
  anomalies: [],
  actions: [],
  summary: null,
  drivers: null,
  missedRevenue: null,
  feed: [],
  healthScore: null,
  shap: null,
  scenario: null,
  businessDna: null,
  rootCause: null,
  loading: false,
  error: null,

  setPeriod: (period) => set({ period }),

  fetchInsights: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ insights: res.data.data });
    }
  },

  fetchAnomalies: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/anomalies', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ anomalies: res.data.data });
    }
  },

  fetchActions: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/actions', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ actions: res.data.data });
    }
  },

  fetchSummary: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/summary', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ summary: res.data.data });
    }
  },

  fetchDrivers: async (storeId, metric = 'revenue') => {
    const { period } = get();
    const res = await apiClient.get('/insights/drivers', { params: { store_id: storeId, period, metric } });
    if (res.data.success && res.data.data) {
      set({ drivers: res.data.data });
    }
  },

  fetchMissedRevenue: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/missed-revenue', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ missedRevenue: res.data.data });
    }
  },

  fetchFeed: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/feed', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ feed: res.data.data });
    }
  },

  fetchHealthScore: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/health-score', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ healthScore: res.data.data });
    }
  },

  fetchShap: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/shap', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ shap: res.data.data });
    }
  },

  runScenario: async (storeId, adjustments) => {
    const { period } = get();
    const res = await apiClient.post(`/insights/scenario?store_id=${storeId}&period=${period}`, adjustments);
    if (res.data.success && res.data.data) {
      set({ scenario: res.data.data });
    }
  },

  fetchBusinessDna: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/business-dna', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ businessDna: res.data.data });
    }
  },

  fetchRootCause: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/insights/root-cause', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ rootCause: res.data.data });
    }
  },

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const results = await Promise.allSettled([
        get().fetchSummary(storeId),
        get().fetchInsights(storeId),
        get().fetchAnomalies(storeId),
        get().fetchActions(storeId),
        get().fetchDrivers(storeId),
        get().fetchMissedRevenue(storeId),
        get().fetchFeed(storeId),
        get().fetchHealthScore(storeId),
        get().fetchShap(storeId),
        get().fetchBusinessDna(storeId),
        get().fetchRootCause(storeId),
      ]);
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length === results.length) {
        set({ error: 'Failed to load insights' });
      }
    } catch {
      set({ error: 'Failed to load insights' });
    } finally {
      set({ loading: false });
    }
  },
}));
