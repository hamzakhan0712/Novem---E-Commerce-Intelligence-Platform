import { useEffect } from 'react';

import { useDashboardStore } from '@/stores/dashboardStore';
import { useStoreStore } from '@/stores/storeStore';
import { useAlertStore } from '@/stores/alertStore';
import { useSyncStore } from '@/stores/syncStore';

export function useDashboardData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const period = useDashboardStore((s) => s.period);
  const metric = useDashboardStore((s) => s.metric);
  const granularity = useDashboardStore((s) => s.granularity);
  const kpis = useDashboardStore((s) => s.kpis);
  const trends = useDashboardStore((s) => s.trends);
  const loading = useDashboardStore((s) => s.loading);
  const error = useDashboardStore((s) => s.error);
  const fetchSummary = useDashboardStore((s) => s.fetchSummary);
  const fetchTrends = useDashboardStore((s) => s.fetchTrends);
  const revenueAtRisk = useDashboardStore((s) => s.revenueAtRisk);
  const fetchRevenueAtRisk = useDashboardStore((s) => s.fetchRevenueAtRisk);
  const checkThresholds = useAlertStore((s) => s.checkThresholds);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);

  useEffect(() => {
    if (activeStoreId) {
      fetchSummary(activeStoreId);
      fetchRevenueAtRisk(activeStoreId);
      checkThresholds(activeStoreId);
    }
  }, [activeStoreId, period, lastSyncTick, fetchSummary, fetchRevenueAtRisk, checkThresholds]);

  useEffect(() => {
    if (activeStoreId) {
      fetchTrends(activeStoreId);
    }
  }, [activeStoreId, metric, granularity, period, lastSyncTick, fetchTrends]);

  return { kpis, trends, revenueAtRisk, loading, error, hasStore: Boolean(activeStoreId) };
}
