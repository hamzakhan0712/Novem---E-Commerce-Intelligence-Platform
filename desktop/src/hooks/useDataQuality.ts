import { useCallback, useEffect, useState } from 'react';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';
import type { ApiResponse } from '@/types/api';
import type { QualityScore } from '@/types/quality';

export function useDataQuality() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const [quality, setQuality] = useState<QualityScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQuality = useCallback(async (storeId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<ApiResponse<QualityScore>>(
        `/dashboard/quality?store_id=${encodeURIComponent(storeId)}`,
      );
      if (res.data.success && res.data.data) {
        setQuality(res.data.data);
      }
    } catch {
      setError('Failed to load data quality score');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeStoreId) {
      fetchQuality(activeStoreId);
    } else {
      setQuality(null);
    }
  }, [activeStoreId, lastSyncTick, fetchQuality]);

  return { quality, loading, error, hasStore: Boolean(activeStoreId) };
}
