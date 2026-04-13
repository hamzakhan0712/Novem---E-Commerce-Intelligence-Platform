import { useEffect } from 'react';

import { useSentimentStore } from '@/stores/sentimentStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

export function useSentimentData() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const period = useSentimentStore((s) => s.period);
  const summary = useSentimentStore((s) => s.summary);
  const trend = useSentimentStore((s) => s.trend);
  const ratings = useSentimentStore((s) => s.ratings);
  const reviews = useSentimentStore((s) => s.reviews);
  const products = useSentimentStore((s) => s.products);
  const keywords = useSentimentStore((s) => s.keywords);
  const loading = useSentimentStore((s) => s.loading);
  const error = useSentimentStore((s) => s.error);
  const analyzing = useSentimentStore((s) => s.analyzing);
  const fetchAll = useSentimentStore((s) => s.fetchAll);
  const analyzeReviews = useSentimentStore((s) => s.analyzeReviews);

  useEffect(() => {
    if (activeStoreId) {
      fetchAll(activeStoreId);
    }
  }, [activeStoreId, period, lastSyncTick, fetchAll]);

  const handleAnalyze = async () => {
    if (activeStoreId) {
      await analyzeReviews(activeStoreId);
      fetchAll(activeStoreId);
    }
  };

  return {
    summary,
    trend,
    ratings,
    reviews,
    products,
    keywords,
    loading,
    error,
    analyzing,
    handleAnalyze,
    hasStore: Boolean(activeStoreId),
  };
}
