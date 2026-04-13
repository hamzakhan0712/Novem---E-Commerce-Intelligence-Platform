import { useEffect } from 'react';

import { useProductStore } from '@/stores/productStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useProductData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const { period, sortBy, summary, topProducts, categories, trend, basket, inventory, lifecycle, stockForecast, stockoutImpact, loading, error, setPeriod, setSortBy, fetchAll } = useProductStore();

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, period, sortBy, lastSyncTick, fetchAll]);

  return { period, sortBy, summary, topProducts, categories, trend, basket, inventory, lifecycle, stockForecast, stockoutImpact, loading, error, setPeriod, setSortBy, hasStore: !!activeStoreId };
}
