import { useEffect } from 'react';

import { useInsightStore } from '@/stores/insightStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useInsightData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const {
    period, insights, anomalies, actions, summary,
    drivers, missedRevenue, feed, healthScore, shap, scenario,
    businessDna, rootCause,
    loading, error, setPeriod, fetchAll, fetchDrivers, runScenario,
  } = useInsightStore();

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, period, lastSyncTick, fetchAll]);

  return {
    period, insights, anomalies, actions, summary,
    drivers, missedRevenue, feed, healthScore, shap, scenario,
    businessDna, rootCause,
    loading, error, setPeriod, fetchDrivers, runScenario,
    hasStore: Boolean(activeStoreId),
    storeId: activeStoreId,
  };
}
