import { create } from 'zustand';

import apiClient from '@/utils/apiClient';

import type { ProductSummary, TopProduct, CategoryBreakdown, ProductPeriod, ProductSort, ProductTrendPoint, BasketAnalysis, InventoryAnalysis, ProductLifecycle, StockForecastData, StockoutImpactData } from '@/types/products';

interface ProductState {
  period: ProductPeriod;
  sortBy: ProductSort;
  summary: ProductSummary | null;
  topProducts: TopProduct[];
  categories: CategoryBreakdown[];
  trend: ProductTrendPoint[];
  basket: BasketAnalysis | null;
  inventory: InventoryAnalysis | null;
  lifecycle: ProductLifecycle | null;
  stockForecast: StockForecastData | null;
  stockoutImpact: StockoutImpactData | null;
  loading: boolean;
  error: string | null;

  setPeriod: (period: ProductPeriod) => void;
  setSortBy: (sortBy: ProductSort) => void;
  fetchSummary: (storeId: string) => Promise<void>;
  fetchTopProducts: (storeId: string) => Promise<void>;
  fetchCategories: (storeId: string) => Promise<void>;
  fetchTrend: (storeId: string) => Promise<void>;
  fetchBasket: (storeId: string) => Promise<void>;
  fetchInventory: (storeId: string) => Promise<void>;
  fetchLifecycle: (storeId: string) => Promise<void>;
  fetchStockForecast: (storeId: string) => Promise<void>;
  fetchStockoutImpact: (storeId: string) => Promise<void>;
  fetchAll: (storeId: string) => Promise<void>;
}

export const useProductStore = create<ProductState>()((set, get) => ({
  period: '30d',
  sortBy: 'revenue',
  summary: null,
  topProducts: [],
  categories: [],
  trend: [],
  basket: null,
  inventory: null,
  lifecycle: null,
  stockForecast: null,
  stockoutImpact: null,
  loading: false,
  error: null,

  setPeriod: (period) => set({ period }),
  setSortBy: (sortBy) => set({ sortBy }),

  fetchSummary: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/summary', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ summary: res.data.data });
    }
  },

  fetchTopProducts: async (storeId) => {
    const { period, sortBy } = get();
    const res = await apiClient.get('/products/top', { params: { store_id: storeId, period, sort_by: sortBy, limit: 20 } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ topProducts: res.data.data });
    }
  },

  fetchCategories: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/categories', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ categories: res.data.data });
    }
  },

  fetchTrend: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/trend', { params: { store_id: storeId, period } });
    if (res.data.success && Array.isArray(res.data.data)) {
      set({ trend: res.data.data });
    }
  },

  fetchBasket: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/basket', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ basket: res.data.data });
    }
  },

  fetchInventory: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/inventory', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ inventory: res.data.data });
    }
  },

  fetchLifecycle: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/lifecycle', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ lifecycle: res.data.data });
    }
  },

  fetchStockForecast: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/stock-forecast', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ stockForecast: res.data.data });
    }
  },

  fetchStockoutImpact: async (storeId) => {
    const { period } = get();
    const res = await apiClient.get('/products/stockout-impact', { params: { store_id: storeId, period } });
    if (res.data.success && res.data.data) {
      set({ stockoutImpact: res.data.data });
    }
  },

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const results = await Promise.allSettled([
        get().fetchSummary(storeId),
        get().fetchTopProducts(storeId),
        get().fetchCategories(storeId),
        get().fetchTrend(storeId),
        get().fetchBasket(storeId),
        get().fetchInventory(storeId),
        get().fetchLifecycle(storeId),
        get().fetchStockForecast(storeId),
        get().fetchStockoutImpact(storeId),
      ]);
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length === results.length) {
        set({ error: 'Failed to load product data' });
      }
    } catch {
      set({ error: 'Failed to load product data' });
    } finally {
      set({ loading: false });
    }
  },
}));
