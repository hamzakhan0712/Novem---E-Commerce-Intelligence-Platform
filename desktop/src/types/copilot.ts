export interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  source?: 'analytics' | 'ollama' | 'system' | 'fallback' | 'error';
  model?: string;
  messageId?: string;
  timestamp: number;
  feedback?: FeedbackRating;
  correctedQuestion?: string;
}

export type FeedbackRating = 1 | -1 | 0;

export interface CopilotAskResponse {
  answer: string;
  source: string;
  model?: string;
  message_id: string;
  corrected_question?: string;
  cached?: boolean;
}

export interface OllamaModel {
  id: string;
  name: string;
  size_gb: number;
  params: string;
  tier: 'starter' | 'mid' | 'advanced';
  description: string;
  installed: boolean;
}

export interface InstalledModelInfo {
  id: string;
  size_bytes: number;
  family: string | null;
  params: string | null;
  quantization: string | null;
}

export interface OllamaStatus {
  available: boolean;
  reason?: string;
  url?: string;
  installed_count?: number;
  installed_models?: InstalledModelInfo[];
}

export interface ModelRecommendation {
  type: 'install' | 'upgrade' | 'switch';
  priority: 'high' | 'medium' | 'low';
  model_id: string;
  title: string;
  description: string;
}

export interface ModelRecommendations {
  status: 'offline' | 'needs_setup' | 'partial' | 'good' | 'complete';
  message: string;
  active_model?: string;
  active_tier?: string;
  recommendations: ModelRecommendation[];
  installed_count: number;
  total_count: number;
}

export interface ConversationStarter {
  category: string;
  icon: string;
  questions: string[];
}

export interface FeedbackStats {
  total_feedback: number;
  positive: number;
  negative: number;
  corrections: number;
  satisfaction_rate: number;
  learning_entries: number;
  recent: { question: string; rating: number; created_at: string }[];
}
