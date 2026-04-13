import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type {
  SentimentSummary,
  SentimentTrendPoint,
  RatingBreakdown,
  ReviewItem,
  ProductSentiment,
  SentimentKeywords,
  SentimentPeriod,
} from '@/types/sentiment';

interface SentimentState {
  period: SentimentPeriod;
  summary: SentimentSummary | null;
  trend: SentimentTrendPoint[];
  ratings: RatingBreakdown[];
  reviews: ReviewItem[];
  products: ProductSentiment[];
  keywords: SentimentKeywords | null;
  loading: boolean;
  error: string | null;
  analyzing: boolean;

  setPeriod: (p: SentimentPeriod) => void;
  fetchAll: (storeId: string) => Promise<void>;
  analyzeReviews: (storeId: string) => Promise<void>;
}

export const useSentimentStore = create<SentimentState>()((set, get) => ({
  period: '30d',
  summary: null,
  trend: [],
  ratings: [],
  reviews: [],
  products: [],
  keywords: null,
  loading: false,
  error: null,
  analyzing: false,

  setPeriod: (p) => set({ period: p }),

  fetchAll: async (storeId) => {
    set({ loading: true, error: null });
    const { period } = get();
    const qs = `store_id=${encodeURIComponent(storeId)}&period=${period}`;
    try {
      const results = await Promise.allSettled([
        apiClient.get<ApiResponse<SentimentSummary>>(`/sentiment/summary?${qs}`),
        apiClient.get<ApiResponse<SentimentTrendPoint[]>>(`/sentiment/trend?${qs}`),
        apiClient.get<ApiResponse<RatingBreakdown[]>>(`/sentiment/ratings?${qs}`),
        apiClient.get<ApiResponse<ReviewItem[]>>(`/sentiment/reviews?${qs}&limit=50`),
        apiClient.get<ApiResponse<ProductSentiment[]>>(`/sentiment/products?${qs}`),
        apiClient.get<ApiResponse<SentimentKeywords>>(`/sentiment/keywords?${qs}`),
      ]);

      if (results[0].status === 'fulfilled' && results[0].value.data.success) {
        set({ summary: results[0].value.data.data ?? null });
      }
      if (results[1].status === 'fulfilled' && results[1].value.data.success) {
        set({ trend: results[1].value.data.data ?? [] });
      }
      if (results[2].status === 'fulfilled' && results[2].value.data.success) {
        set({ ratings: results[2].value.data.data ?? [] });
      }
      if (results[3].status === 'fulfilled' && results[3].value.data.success) {
        set({ reviews: results[3].value.data.data ?? [] });
      }
      if (results[4].status === 'fulfilled' && results[4].value.data.success) {
        set({ products: results[4].value.data.data ?? [] });
      }
      if (results[5].status === 'fulfilled' && results[5].value.data.success) {
        set({ keywords: results[5].value.data.data ?? null });
      }

      const allFailed = results.every((r) => r.status === 'rejected');
      if (allFailed) {
        set({ error: 'Failed to load sentiment data' });
      }
    } catch {
      set({ error: 'Failed to load sentiment data' });
    } finally {
      set({ loading: false });
    }
  },

  analyzeReviews: async (storeId) => {
    set({ analyzing: true });
    try {
      await apiClient.post(`/sentiment/analyze?store_id=${encodeURIComponent(storeId)}`);
    } catch {
      // silently fail — user will see results on refetch
    } finally {
      set({ analyzing: false });
    }
  },
}));
