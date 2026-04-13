import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type { Alert, AlertsPage } from '@/types/alerts';

interface AlertState {
  alerts: Alert[];
  total: number;
  unreadCount: number;
  loading: boolean;
  error: string | null;

  fetchAlerts: (storeId: string | null) => Promise<void>;
  fetchUnreadCount: (storeId: string | null) => Promise<void>;
  markRead: (alertIds: string[]) => Promise<void>;
  markAllRead: (storeId: string | null) => Promise<void>;
  deleteAlert: (alertId: string) => Promise<void>;
  checkThresholds: (storeId: string) => Promise<void>;
}

export const useAlertStore = create<AlertState>()((set, get) => ({
  alerts: [],
  total: 0,
  unreadCount: 0,
  loading: false,
  error: null,

  fetchAlerts: async (storeId) => {
    set({ loading: true, error: null });
    try {
      const params = storeId ? `?store_id=${encodeURIComponent(storeId)}&page_size=50` : '?page_size=50';
      const res = await apiClient.get<ApiResponse<AlertsPage>>(`/alerts${params}`);
      if (res.data.success && res.data.data) {
        set({
          alerts: res.data.data.items,
          total: res.data.data.total,
        });
      }
    } catch {
      set({ error: 'Failed to load alerts' });
    } finally {
      set({ loading: false });
    }
  },

  fetchUnreadCount: async (storeId) => {
    try {
      const params = storeId ? `?store_id=${encodeURIComponent(storeId)}` : '';
      const res = await apiClient.get<ApiResponse<{ count: number }>>(`/alerts/unread-count${params}`);
      if (res.data.success && res.data.data) {
        set({ unreadCount: res.data.data.count });
      }
    } catch {
      // Silent fail for badge count
    }
  },

  markRead: async (alertIds) => {
    try {
      await apiClient.post('/alerts/mark-read', { alert_ids: alertIds });
      set((s) => ({
        alerts: s.alerts.map((a) =>
          alertIds.includes(a.id) ? { ...a, is_read: true } : a,
        ),
        unreadCount: Math.max(0, s.unreadCount - alertIds.length),
      }));
    } catch {
      // Silent
    }
  },

  markAllRead: async (storeId) => {
    try {
      const params = storeId ? `?store_id=${encodeURIComponent(storeId)}` : '';
      await apiClient.post(`/alerts/mark-all-read${params}`);
      set((s) => ({
        alerts: s.alerts.map((a) => ({ ...a, is_read: true })),
        unreadCount: 0,
      }));
    } catch {
      // Silent
    }
  },

  deleteAlert: async (alertId) => {
    try {
      await apiClient.delete(`/alerts/${alertId}`);
      const { alerts, total, unreadCount } = get();
      const removed = alerts.find((a) => a.id === alertId);
      set({
        alerts: alerts.filter((a) => a.id !== alertId),
        total: total - 1,
        unreadCount: removed && !removed.is_read ? unreadCount - 1 : unreadCount,
      });
    } catch {
      // Silent
    }
  },

  checkThresholds: async (storeId) => {
    try {
      await apiClient.post(`/alerts/check-thresholds?store_id=${encodeURIComponent(storeId)}`);
      const { fetchAlerts, fetchUnreadCount } = get();
      await Promise.all([fetchAlerts(storeId), fetchUnreadCount(storeId)]);
    } catch {
      // Silent
    }
  },
}));
