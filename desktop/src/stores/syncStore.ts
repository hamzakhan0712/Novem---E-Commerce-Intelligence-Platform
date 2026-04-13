import { create } from 'zustand';

import apiClient from '@/utils/apiClient';

export interface SyncActivity {
  id: string;
  data_type: string;
  source_type: string;
  row_count_raw: number;
  status: string;
  imported_at: string;
}

interface SyncState {
  /** Currently syncing — show the banner */
  isSyncing: boolean;
  /** Label for what's being synced right now */
  syncLabel: string;
  /** Timestamp when current sync started */
  syncStartedAt: number | null;
  /** Most recent completed sync events */
  recentActivity: SyncActivity[];
  /** Incrementing counter — bumped after every successful sync so consumers can react */
  lastSyncTick: number;
  /** ID of most recent import_history entry — used to detect new webhook data */
  lastKnownImportId: string | null;

  startSync: (label: string) => void;
  endSync: () => void;
  fetchActivity: (storeId: string) => Promise<void>;
  /** Call this to tell all listeners new data arrived */
  notifyDataChanged: () => void;
  /** Lightweight poll — checks for new import_history entries from webhooks */
  pollForNewData: (storeId: string) => Promise<void>;
}

export const useSyncStore = create<SyncState>()((set, get) => ({
  isSyncing: false,
  syncLabel: '',
  syncStartedAt: null,
  recentActivity: [],
  lastSyncTick: 0,
  lastKnownImportId: null,

  startSync: (label) =>
    set({ isSyncing: true, syncLabel: label, syncStartedAt: Date.now() }),

  endSync: () =>
    set((s) => ({
      isSyncing: false,
      syncLabel: '',
      syncStartedAt: null,
      lastSyncTick: s.lastSyncTick + 1,
    })),

  fetchActivity: async (storeId) => {
    try {
      const res = await apiClient.get(`/sync/history/${storeId}?limit=5`);
      const data = res.data?.data ?? [];
      set({ recentActivity: data });
      if (data.length > 0 && !get().lastKnownImportId) {
        set({ lastKnownImportId: data[0].id });
      }
    } catch {
      // non-critical
    }
  },

  notifyDataChanged: () =>
    set((s) => ({ lastSyncTick: s.lastSyncTick + 1 })),

  pollForNewData: async (storeId) => {
    if (get().isSyncing) return;
    try {
      const res = await apiClient.get(`/sync/history/${storeId}?limit=1`);
      const entries = res.data?.data ?? [];
      if (entries.length === 0) return;
      const latestId = entries[0].id;
      const known = get().lastKnownImportId;
      if (known && latestId !== known) {
        set({ lastKnownImportId: latestId });
        get().notifyDataChanged();
      } else if (!known) {
        set({ lastKnownImportId: latestId });
      }
    } catch {
      // non-critical
    }
  },
}));
