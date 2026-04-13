import { create } from 'zustand';

import apiClient from '@/utils/apiClient';

import type { CustomerSummary, TopCustomer, CustomerSegment, CustomerGrowthPoint, CustomerPeriod, ChurnPrediction, CohortReplay } from '@/types/customers';

interface CustomerState {
  period: CustomerPeriod;
  summary: CustomerSummary | null;
  topCustomers: TopCustomer[];
  segments: CustomerSegment[];
  growth: CustomerGrowthPoint[];
  churn: ChurnPrediction | null;
  cohortReplay: CohortReplay | null;
  loading: boolean;
  error: string | null;

  setPeriod: (period: CustomerPeriod) => void;
  fetchSummary: (storeId: string) => Promise<void>;
  fetchTopCustomers: (storeId: string) => Promise<void>;
  fetchSegments: (storeId: string) => Promise<void>;
  fetchGrowth: (storeId: string) => Promise<void>;
  fetchChurn: (storeId: string) => Promise<void>;
  fetchCohortReplay: (storeId: string, replayMonth?: string) => Promise<void>;
  fetchAll: (storeId: string) => Promise<void>;
}

export const useCustomerStore = create<CustomerState>()((set, get) => ({
  period: '30d',
  summary: null,
  topCustomers: [],
  segments: [],
  growth: [],
  churn: null,
  cohortReplay: null,
  loading: false,
  error: null,

  setPeriod: (period) => set({ period }),

  fetchSummary: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/customers/summary', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ summary: res.data.data });
    }
  },

  fetchTopCustomers: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/customers/top', { params: { store_id: storeId, period, limit: 20 } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ topCustomers: res.data.data });
    }
  },

  fetchSegments: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/customers/segments', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ segments: res.data.data });
    }
  },

  fetchGrowth: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/customers/growth', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ growth: res.data.data });
    }
  },

  fetchChurn: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/customers/churn', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ churn: res.data.data });
    }
  },

  fetchCohortReplay: async (storeId, replayMonth) => {
    const res = await apiClient.get('/customers/cohort-replay', {
      params: { store_id: storeId, ...(replayMonth ? { replay_month: replayMonth } : {}) },
    });
    if (res.data.success && res.data.data) {
      set({ cohortReplay: res.data.data });
    }
  },

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const results = await Promise.allSettled([
        get().fetchSummary(storeId),
        get().fetchTopCustomers(storeId),
        get().fetchSegments(storeId),
        get().fetchGrowth(storeId),
        get().fetchChurn(storeId),
        get().fetchCohortReplay(storeId),
      ]);
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length === results.length) {
        set({ error: 'Failed to load customer data' });
      }
    } catch {
      set({ error: 'Failed to load customer data' });
    } finally {
      set({ loading: false });
    }
  },
}));
