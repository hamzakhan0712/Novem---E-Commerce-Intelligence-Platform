import { useEffect } from 'react';

import { useStoreStore } from '@/stores/storeStore';

export function useStores() {
  const stores = useStoreStore((s) => s.stores);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const loading = useStoreStore((s) => s.loading);
  const error = useStoreStore((s) => s.error);
  const fetchStores = useStoreStore((s) => s.fetchStores);

  useEffect(() => {
    if (stores.length === 0) {
      fetchStores();
    }
  }, [stores.length, fetchStores]);

  const activeStore = stores.find((s) => s.id === activeStoreId) ?? null;

  return { stores, activeStore, activeStoreId, loading, error };
}
