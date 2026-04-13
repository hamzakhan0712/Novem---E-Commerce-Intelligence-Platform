import { useState, useEffect } from 'react';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import type { ApiResponse } from '@/types/api';

interface BenchmarkComparison {
  metric: string;
  label: string;
  benchmark: number;
  store_value: number | null;
  difference: number | null;
  difference_pct: number | null;
  status: 'above' | 'below' | 'on_par' | 'no_data';
  lower_is_better: boolean;
}

interface BenchmarkData {
  industry: string;
  comparisons: BenchmarkComparison[];
  available_industries: string[];
}

export function useBenchmarkData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const [data, setData] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeStoreId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .get<ApiResponse<BenchmarkData>>('/benchmarks/compare', {
        params: { store_id: activeStoreId },
      })
      .then((res) => {
        if (!cancelled && res.data.success) {
          setData(res.data.data ?? null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load benchmarks');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [activeStoreId]);

  return { data, loading, error };
}
