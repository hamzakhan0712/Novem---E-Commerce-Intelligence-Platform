import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';

type TableCounts = Record<string, number>;

/**
 * Defines which DuckDB tables each page requires to be non-empty.
 * 'any' = at least one table must have data.
 */
export const PAGE_TABLE_REQUIREMENTS: Record<string, string[] | 'any'> = {
  dashboard: ['orders'],
  customers: ['orders', 'customers'],
  products: ['orders', 'products'],
  marketing: ['ad_spend'],
  insights: ['orders'],
  forecasting: ['orders'],
  sentiment: ['reviews'],
  copilot: ['orders'],
  reports: ['orders'],
  'data-viewer': 'any',
};

interface DataAvailabilityState {
  tableCounts: TableCounts;
  loading: boolean;
  loaded: boolean;

  fetchTableCounts: (storeId: string) => Promise<void>;
  reset: () => void;
  isPageAccessible: (pageKey: string) => boolean;
  hasAnyData: () => boolean;
}

export const useDataAvailabilityStore = create<DataAvailabilityState>()((set, get) => ({
  tableCounts: {},
  loading: false,
  loaded: false,

  fetchTableCounts: async (storeId: string) => {
    set({ loading: true });
    try {
      const res = await apiClient.get<ApiResponse<TableCounts>>(
        '/data-viewer/tables',
        { params: { store_id: storeId } },
      );
      set({ tableCounts: res.data.data ?? {}, loading: false, loaded: true });
    } catch {
      set({ tableCounts: {}, loading: false, loaded: true });
    }
  },

  reset: () => set({ tableCounts: {}, loading: false, loaded: false }),

  isPageAccessible: (pageKey: string) => {
    const { tableCounts } = get();
    const requirements = PAGE_TABLE_REQUIREMENTS[pageKey];
    if (!requirements) return true;
    if (requirements === 'any') {
      return Object.values(tableCounts).some((count) => count > 0);
    }
    return requirements.every((table) => (tableCounts[table] ?? 0) > 0);
  },

  hasAnyData: () => {
    const { tableCounts } = get();
    return Object.values(tableCounts).some((count) => count > 0);
  },
}));
