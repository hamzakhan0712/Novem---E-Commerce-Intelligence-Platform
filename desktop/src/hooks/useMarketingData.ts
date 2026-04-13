import { useEffect } from 'react';

import { useMarketingStore } from '@/stores/marketingStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useMarketingData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const {
    period, granularity, campaignSort,
    kpis, channels, trends, campaigns, wastedSpend, categoryRoi,
    loading, error,
    setPeriod, setGranularity, setCampaignSort, fetchAll, fetchTrends, fetchCampaigns,
  } = useMarketingStore();

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, period, lastSyncTick, fetchAll]);

  useEffect(() => {
    if (activeStoreId) {
      fetchTrends(activeStoreId);
    }
  }, [activeStoreId, granularity, fetchTrends]);

  useEffect(() => {
    if (activeStoreId) {
      fetchCampaigns(activeStoreId);
    }
  }, [activeStoreId, campaignSort, fetchCampaigns]);

  return {
    period, granularity, campaignSort,
    kpis, channels, trends, campaigns, wastedSpend, categoryRoi,
    loading, error,
    setPeriod, setGranularity, setCampaignSort,
    hasStore: !!activeStoreId,
  };
}
