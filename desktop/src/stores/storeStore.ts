import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type { Store, CreateStoreRequest, UpdateStoreRequest } from '@/types/store';

const ACTIVE_STORE_KEY = 'novem-active-store';

interface StoreState {
  stores: Store[];
  activeStoreId: string | null;
  loading: boolean;
  error: string | null;

  fetchStores: () => Promise<void>;
  createStore: (req: CreateStoreRequest) => Promise<Store | null>;
  updateStore: (storeId: string, req: UpdateStoreRequest) => Promise<void>;
  deleteStore: (storeId: string) => Promise<void>;
  setActiveStore: (storeId: string | null) => void;
}

export const useStoreStore = create<StoreState>()((set, get) => ({
  stores: [],
  activeStoreId: localStorage.getItem(ACTIVE_STORE_KEY),
  loading: false,
  error: null,

  fetchStores: async () => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.get<ApiResponse<Store[]>>('/stores');
      const stores = res.data.data ?? [];

      const currentActive = get().activeStoreId;
      const activeExists = stores.some((s) => s.id === currentActive);
      const activeStoreId = activeExists
        ? currentActive
        : stores.length > 0
          ? stores[0].id
          : null;

      if (activeStoreId !== currentActive) {
        if (activeStoreId) {
          localStorage.setItem(ACTIVE_STORE_KEY, activeStoreId);
        } else {
          localStorage.removeItem(ACTIVE_STORE_KEY);
        }
      }

      set({ stores, activeStoreId, loading: false });
    } catch {
      set({ loading: false, error: 'Failed to load stores' });
    }
  },

  createStore: async (req) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post<ApiResponse<Store>>('/stores', req);
      const store = res.data.data;
      if (store) {
        const stores = [...get().stores, store];
        localStorage.setItem(ACTIVE_STORE_KEY, store.id);
        set({ stores, activeStoreId: store.id, loading: false });
        return store;
      }
      set({ loading: false });
      return null;
    } catch {
      set({ loading: false, error: 'Failed to create store' });
      return null;
    }
  },

  updateStore: async (storeId, req) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.patch<ApiResponse<Store>>(`/stores/${storeId}`, req);
      const updated = res.data.data;
      if (updated) {
        const stores = get().stores.map((s) => (s.id === storeId ? updated : s));
        set({ stores, loading: false });
      }
    } catch {
      set({ loading: false, error: 'Failed to update store' });
    }
  },

  deleteStore: async (storeId) => {
    set({ loading: true, error: null });
    try {
      await apiClient.delete(`/stores/${storeId}`);
      const stores = get().stores.filter((s) => s.id !== storeId);
      const activeStoreId =
        get().activeStoreId === storeId
          ? stores.length > 0
            ? stores[0].id
            : null
          : get().activeStoreId;

      if (activeStoreId) {
        localStorage.setItem(ACTIVE_STORE_KEY, activeStoreId);
      } else {
        localStorage.removeItem(ACTIVE_STORE_KEY);
      }

      set({ stores, activeStoreId, loading: false });
    } catch {
      set({ loading: false, error: 'Failed to delete store' });
    }
  },

  setActiveStore: (storeId) => {
    if (storeId) {
      localStorage.setItem(ACTIVE_STORE_KEY, storeId);
    } else {
      localStorage.removeItem(ACTIVE_STORE_KEY);
    }
    set({ activeStoreId: storeId });
  },
}));
