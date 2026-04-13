import { useState, useEffect, useCallback } from 'react';

import apiClient from '@/utils/apiClient';

import type { DataProfileResponse } from '@/types/ingestion';

export function useDataProfile(storeId: string | null, dataType?: string) {
  const [data, setData] = useState<DataProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!storeId || !dataType) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ success: boolean; data: DataProfileResponse }>(
        '/ingestion/data-profile',
        { params: { store_id: storeId, data_type: dataType } },
      );
      if (res.data.success) {
        setData(res.data.data);
      }
    } catch {
      setError('Failed to load data profile');
    } finally {
      setLoading(false);
    }
  }, [storeId, dataType]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
