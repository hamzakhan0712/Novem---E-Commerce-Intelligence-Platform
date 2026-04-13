import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';
import type {
  CopilotAskResponse,
  CopilotMessage,
  ConversationStarter,
  FeedbackRating,
  FeedbackStats,
  ModelRecommendations,
  OllamaModel,
  OllamaStatus,
} from '@/types/copilot';

interface CopilotState {
  messages: CopilotMessage[];
  suggestions: string[];
  starters: ConversationStarter[];
  loading: boolean;

  ollamaStatus: OllamaStatus | null;
  models: OllamaModel[];
  activeModel: string;
  installingModel: string | null;
  statusLoading: boolean;
  recommendations: ModelRecommendations | null;

  feedbackStats: FeedbackStats | null;

  askQuestion: (storeId: string, question: string) => Promise<void>;
  submitFeedback: (storeId: string, messageId: string, rating: FeedbackRating, correction?: string) => Promise<void>;
  fetchFeedbackStats: (storeId: string) => Promise<void>;
  warmupModel: () => Promise<void>;
  fetchSuggestions: () => Promise<void>;
  fetchStarters: () => Promise<void>;
  fetchStatus: () => Promise<void>;
  fetchModels: () => Promise<void>;
  fetchActiveModel: () => Promise<void>;
  fetchRecommendations: () => Promise<void>;
  setActiveModel: (modelId: string) => Promise<void>;
  installModel: (modelId: string) => Promise<void>;
  deleteModel: (modelId: string) => Promise<void>;
  clearMessages: () => void;
}

let messageId = 0;

export const useCopilotStore = create<CopilotState>()((set, get) => ({
  messages: [],
  suggestions: [],
  starters: [],
  loading: false,

  ollamaStatus: null,
  models: [],
  activeModel: 'llama3.2:latest',
  installingModel: null,
  statusLoading: false,
  recommendations: null,

  feedbackStats: null,

  askQuestion: async (storeId, question) => {
    const userMsg: CopilotMessage = {
      id: `msg-${++messageId}`,
      role: 'user',
      content: question,
      timestamp: Date.now(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], loading: true }));

    try {
      // Build conversation history from last 10 messages for context
      const history = get().messages
        .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.source !== 'error'))
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await apiClient.post<ApiResponse<CopilotAskResponse>>(
        '/copilot/ask',
        { store_id: storeId, question, conversation_history: history },
        { timeout: 120_000 },
      );
      if (res.data.success && res.data.data) {
        const assistantMsg: CopilotMessage = {
          id: `msg-${++messageId}`,
          role: 'assistant',
          content: res.data.data.answer,
          source: res.data.data.source as CopilotMessage['source'],
          model: res.data.data.model,
          messageId: res.data.data.message_id,
          correctedQuestion: res.data.data.corrected_question,
          timestamp: Date.now(),
        };
        set((s) => ({ messages: [...s.messages, assistantMsg], loading: false }));
      } else {
        set({ loading: false });
      }
    } catch (err) {
      const isTimeout = err instanceof Error && (err.message.includes('timeout') || err.message.includes('ECONNABORTED'));
      const errorMsg: CopilotMessage = {
        id: `msg-${++messageId}`,
        role: 'assistant',
        content: isTimeout
          ? 'The AI model took too long to respond. This can happen on the first query while the model loads. Please try again.'
          : 'Sorry, I couldn\'t process that question. Please try again.',
        source: 'error',
        timestamp: Date.now(),
      };
      set((s) => ({ messages: [...s.messages, errorMsg], loading: false }));
    }
  },

  submitFeedback: async (storeId, msgId, rating, correction) => {
    const msg = get().messages.find((m) => m.messageId === msgId);
    if (!msg) return;

    const userMsg = get().messages
      .slice(0, get().messages.indexOf(msg))
      .reverse()
      .find((m) => m.role === 'user');

    try {
      await apiClient.post('/copilot/feedback', {
        store_id: storeId,
        message_id: msgId,
        question: userMsg?.content ?? '',
        answer: msg.content,
        source: msg.source ?? 'system',
        model: msg.model ?? null,
        rating,
        correction: correction ?? null,
      });

      set((s) => ({
        messages: s.messages.map((m) =>
          m.messageId === msgId ? { ...m, feedback: rating } : m,
        ),
      }));
    } catch {
      // feedback submission failed silently
    }
  },

  fetchFeedbackStats: async (storeId) => {
    try {
      const res = await apiClient.get<ApiResponse<FeedbackStats>>(
        `/copilot/feedback/stats/${encodeURIComponent(storeId)}`,
      );
      if (res.data.success && res.data.data) {
        set({ feedbackStats: res.data.data });
      }
    } catch {
      // keep null
    }
  },

  warmupModel: async () => {
    try {
      await apiClient.post('/copilot/warmup', {}, { timeout: 60_000 });
    } catch {
      // warmup is fire-and-forget
    }
  },

  fetchSuggestions: async () => {
    try {
      const res = await apiClient.get<ApiResponse<string[]>>('/copilot/suggestions');
      if (res.data.success && res.data.data) {
        set({ suggestions: res.data.data });
      }
    } catch {
      // keep defaults
    }
  },

  fetchStarters: async () => {
    try {
      const res = await apiClient.get<ApiResponse<ConversationStarter[]>>('/copilot/starters');
      if (res.data.success && res.data.data) {
        set({ starters: res.data.data });
      }
    } catch {
      // keep defaults
    }
  },

  fetchStatus: async () => {
    set({ statusLoading: true });
    try {
      const res = await apiClient.get<ApiResponse<OllamaStatus>>('/copilot/status');
      if (res.data.success && res.data.data) {
        set({ ollamaStatus: res.data.data, statusLoading: false });
      }
    } catch {
      set({ ollamaStatus: { available: false, reason: 'Connection failed' }, statusLoading: false });
    }
  },

  fetchModels: async () => {
    try {
      const res = await apiClient.get<ApiResponse<OllamaModel[]>>('/copilot/models');
      if (res.data.success && res.data.data) {
        set({ models: res.data.data });
      }
    } catch {
      // keep empty
    }
  },

  fetchActiveModel: async () => {
    try {
      const res = await apiClient.get<ApiResponse<{ model: string }>>('/copilot/models/active');
      if (res.data.success && res.data.data) {
        set({ activeModel: res.data.data.model });
      }
    } catch {
      // keep default
    }
  },

  fetchRecommendations: async () => {
    try {
      const res = await apiClient.get<ApiResponse<ModelRecommendations>>('/copilot/models/recommendations');
      if (res.data.success && res.data.data) {
        set({ recommendations: res.data.data });
      }
    } catch {
      // keep null
    }
  },

  setActiveModel: async (modelId) => {
    try {
      await apiClient.put('/copilot/models/active', { model_id: modelId });
      set({ activeModel: modelId });
      get().fetchRecommendations();
    } catch {
      // ignore
    }
  },

  installModel: async (modelId) => {
    set({ installingModel: modelId });
    try {
      await apiClient.post('/copilot/models/install', { model_id: modelId });
      set({ installingModel: null });
      get().fetchModels();
      get().fetchRecommendations();
    } catch {
      set({ installingModel: null });
    }
  },

  deleteModel: async (modelId) => {
    try {
      await apiClient.delete(`/copilot/models/${encodeURIComponent(modelId)}`);
      get().fetchModels();
      get().fetchRecommendations();
    } catch {
      // ignore
    }
  },

  clearMessages: () => set({ messages: [] }),
}));
