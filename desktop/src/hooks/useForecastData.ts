import { useEffect } from 'react';

import { useForecastStore } from '@/stores/forecastStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useForecastData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const metric = useForecastStore((s) => s.metric);
  const horizonDays = useForecastStore((s) => s.horizonDays);
  const forecast = useForecastStore((s) => s.forecast);
  const metricsOverview = useForecastStore((s) => s.metricsOverview);
  const loading = useForecastStore((s) => s.loading);
  const error = useForecastStore((s) => s.error);
  const fetchAll = useForecastStore((s) => s.fetchAll);

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, metric, horizonDays, lastSyncTick, fetchAll]);

  return { forecast, metricsOverview, loading, error, hasStore: Boolean(activeStoreId) };
}
