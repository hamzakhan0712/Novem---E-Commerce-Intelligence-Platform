import { useEffect } from 'react';

import { useAlertStore } from '@/stores/alertStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useAlertData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const alerts = useAlertStore((s) => s.alerts);
  const total = useAlertStore((s) => s.total);
  const unreadCount = useAlertStore((s) => s.unreadCount);
  const loading = useAlertStore((s) => s.loading);
  const error = useAlertStore((s) => s.error);
  const fetchAlerts = useAlertStore((s) => s.fetchAlerts);
  const fetchUnreadCount = useAlertStore((s) => s.fetchUnreadCount);

  useEffect(() => {
    fetchAlerts(activeStoreId);
    fetchUnreadCount(activeStoreId);
  }, [activeStoreId, lastSyncTick, fetchAlerts, fetchUnreadCount]);

  return { alerts, total, unreadCount, loading, error, hasStore: Boolean(activeStoreId) };
}
