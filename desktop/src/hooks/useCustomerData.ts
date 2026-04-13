import { useEffect } from 'react';

import { useCustomerStore } from '@/stores/customerStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useCustomerData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const { period, summary, topCustomers, segments, growth, churn, cohortReplay, loading, error, setPeriod, fetchAll, fetchCohortReplay } = useCustomerStore();

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, period, lastSyncTick, fetchAll]);

  return { period, summary, topCustomers, segments, growth, churn, cohortReplay, loading, error, setPeriod, fetchCohortReplay, hasStore: !!activeStoreId, storeId: activeStoreId };
}
