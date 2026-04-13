import { useEffect, useRef } from 'react';

import { useCopilotStore } from '@/stores/copilotStore';
import type { FeedbackRating } from '@/types/copilot';

export function useCopilotData() {
  const store = useCopilotStore();
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    Promise.allSettled([
      store.fetchSuggestions(),
      store.fetchStarters(),
      store.fetchStatus(),
      store.fetchModels(),
      store.fetchActiveModel(),
      store.fetchRecommendations(),
      store.warmupModel(),
    ]);
  }, []);

  return {
    messages: store.messages,
    suggestions: store.suggestions,
    starters: store.starters,
    loading: store.loading,

    ollamaStatus: store.ollamaStatus,
    models: store.models,
    activeModel: store.activeModel,
    installingModel: store.installingModel,
    statusLoading: store.statusLoading,
    recommendations: store.recommendations,

    feedbackStats: store.feedbackStats,

    askQuestion: store.askQuestion,
    submitFeedback: store.submitFeedback as (storeId: string, messageId: string, rating: FeedbackRating, correction?: string) => Promise<void>,
    fetchFeedbackStats: store.fetchFeedbackStats,
    warmupModel: store.warmupModel,
    clearMessages: store.clearMessages,
    setActiveModel: store.setActiveModel,
    installModel: store.installModel,
    deleteModel: store.deleteModel,
    refreshStatus: store.fetchStatus,
    refreshModels: store.fetchModels,
    refreshRecommendations: store.fetchRecommendations,
  };
}
