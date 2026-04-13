import { create } from 'zustand';

import apiClient from '@/utils/apiClient';

import type {
  MarketingPeriod,
  MarketingGranularity,
  CampaignSortField,
  MarketingKpiResponse,
  ChannelPerformance,
  ChannelTrendPoint,
  CampaignPerformance,
  WastedSpendData,
  CategoryRoi,
} from '@/types/marketing';

interface MarketingState {
  period: MarketingPeriod;
  granularity: MarketingGranularity;
  campaignSort: CampaignSortField;
  kpis: MarketingKpiResponse | null;
  channels: ChannelPerformance[];
  trends: ChannelTrendPoint[];
  campaigns: CampaignPerformance[];
  wastedSpend: WastedSpendData | null;
  categoryRoi: CategoryRoi[];
  loading: boolean;
  error: string | null;

  setPeriod: (period: MarketingPeriod) => void;
  setGranularity: (granularity: MarketingGranularity) => void;
  setCampaignSort: (sort: CampaignSortField) => void;
  fetchSummary: (storeId: string) => Promise<void>;
  fetchChannels: (storeId: string) => Promise<void>;
  fetchTrends: (storeId: string) => Promise<void>;
  fetchCampaigns: (storeId: string) => Promise<void>;
  fetchWastedSpend: (storeId: string) => Promise<void>;
  fetchCategoryRoi: (storeId: string) => Promise<void>;
  fetchAll: (storeId: string) => Promise<void>;
}

export const useMarketingStore = create<MarketingState>()((set, get) => ({
  period: '30d',
  granularity: 'daily',
  campaignSort: 'roas',
  kpis: null,
  channels: [],
  trends: [],
  campaigns: [],
  wastedSpend: null,
  categoryRoi: [],
  loading: false,
  error: null,

  setPeriod: (period) => set({ period }),
  setGranularity: (granularity) => set({ granularity }),
  setCampaignSort: (campaignSort) => set({ campaignSort }),

  fetchSummary: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/marketing/summary', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ kpis: res.data.data });
    }
  },

  fetchChannels: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/marketing/channels', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ channels: res.data.data });
    }
  },

  fetchTrends: async (storeId) => {
    const { period, granularity } = get();
    const res = await apiClient.get('/marketing/trends', { params: { store_id: storeId, period, granularity } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ trends: res.data.data });
    }
  },

  fetchCampaigns: async (storeId) => {
    const { period, campaignSort } = get();
    const res = await apiClient.get('/marketing/campaigns', { params: { store_id: storeId, period, sort_by: campaignSort, limit: 50 } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ campaigns: res.data.data });
    }
  },

  fetchWastedSpend: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/marketing/wasted-spend', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ wastedSpend: res.data.data });
    }
  },

  fetchCategoryRoi: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/marketing/category-roi', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data?.categories) {
      set({ categoryRoi: res.data.data.categories });
    }
  },

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const results = await Promise.allSettled([
        get().fetchSummary(storeId),
        get().fetchChannels(storeId),
        get().fetchTrends(storeId),
        get().fetchCampaigns(storeId),
        get().fetchWastedSpend(storeId).catch(() => {}),
        get().fetchCategoryRoi(storeId).catch(() => {}),
      ]);
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length >= 4) {
        set({ error: 'Failed to load marketing data' });
      }
    } catch {
      set({ error: 'Failed to load marketing data' });
    } finally {
      set({ loading: false });
    }
  },
}));
