export interface Insight {
  type: string;
  category: string;
  severity: 'positive' | 'negative' | 'warning' | 'info';
  priority: number;
  title: string;
  message: string;
  suggestion: string | null;
  confidence?: number;
}

export interface Anomaly {
  date: string;
  metric: string;
  value: number;
  expected: number;
  z_score: number;
  direction: 'spike' | 'drop';
  severity: 'high' | 'medium' | 'low';
  message: string;
  confidence?: number;
  detected_at?: string;
  time_to_detection_hours?: number | null;
}

export interface RecommendedAction {
  rank: number;
  priority: 'high' | 'medium' | 'low';
  category: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  impact_dollars?: number;
  confidence?: number;
}

export interface InsightSummary {
  total_insights: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  anomaly_count: number;
  action_count: number;
  categories: string[];
}

export type InsightPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';

// Causal Breakdown (now: Revenue Attribution)
export interface CausalDriver {
  driver: string;
  impact: number;
  direction: 'up' | 'down';
  detail: string;
}

export interface CausalBreakdown {
  metric: string;
  current_value: number;
  previous_value: number;
  change_amount: number;
  change_pct: number;
  period: string;
  drivers: CausalDriver[];
  narrative: string;
}

// Missed Revenue
export interface MissedRevenueItem {
  type: 'refund' | 'churn' | 'stockout';
  amount: number;
  description: string;
  product?: string;
  reason?: string;
  count?: number;
  customer_id?: string;
}

export interface MissedRevenueBreakdown {
  total: number;
  count: number;
  items: MissedRevenueItem[];
}

export interface MissedRevenueSummary {
  total_missed_revenue: number;
  breakdown: {
    refunds: MissedRevenueBreakdown;
    churned_customers: MissedRevenueBreakdown;
    stockout_signals: MissedRevenueBreakdown;
  };
  opportunities: MissedRevenueItem[];
  period: string;
}

// Insight Feed
export interface FeedItem {
  id: string;
  feed_type: 'insight' | 'anomaly' | 'action' | 'causal' | 'missed_revenue';
  severity: 'positive' | 'negative' | 'warning' | 'info';
  priority: number;
  title: string;
  message: string;
  suggestion?: string;
  category: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Business Health Score
export interface HealthScoreComponent {
  score: number;
  weight: number;
  detail: string;
}

export interface BusinessHealthScore {
  overall_score: number;
  label: string;
  components: {
    revenue_growth: HealthScoreComponent;
    customer_health: HealthScoreComponent;
    operational_efficiency: HealthScoreComponent;
    growth_momentum: HealthScoreComponent;
  };
  period: string;
}

// SHAP Explainability
export interface ShapFeature {
  feature: string;
  importance: number;
  label: string;
}

export interface ShapDriver {
  feature: string;
  label: string;
  shap_value: number;
  feature_value: number;
  direction: 'increases_churn' | 'decreases_churn';
}

export interface ShapCustomerExplanation {
  customer_id: string;
  churn_probability: number;
  top_drivers: ShapDriver[];
}

export interface ShapExplanation {
  model: string;
  global_importance: ShapFeature[];
  sample_explanations: ShapCustomerExplanation[];
  summary: {
    total_customers: number;
    features_used: number;
    model_accuracy: number;
    churn_threshold_days?: number;
    churned_count?: number;
    active_count?: number;
  };
  message?: string;
}

// What-If Scenario Simulator
export interface ScenarioImpact {
  lever: string;
  adjustment: string;
  revenue_impact: number;
  detail: string;
}

export interface ScenarioResult {
  baseline: Record<string, number>;
  projected: Record<string, number>;
  total_impact: number;
  impact_pct: number;
  adjustments: Record<string, number>;
  impacts: ScenarioImpact[];
  period: string;
  assumptions?: string[];
  disclaimer?: string;
  message?: string;
}

// Business DNA — Store Fingerprinting
export interface DnaDimension {
  name: string;
  score: number;
  label: string;
  detail: string;
}

export interface BusinessDna {
  dimensions: DnaDimension[];
  archetype: string;
  archetype_description: string;
  summary: string;
  period: string;
  message?: string;
}

// Root Cause Narrative
export interface DrillDown {
  dimension: string;
  top_contributor: string;
  impact: number | null;
  detail: string;
}

export interface PrimaryCause {
  dimension: string;
  contributor: string;
  impact: number;
  impact_pct: number;
  detail: string;
}

export interface RootCauseNarrative {
  verdict: string;
  direction: 'up' | 'down' | 'flat';
  change_pct: number;
  change_amount: number;
  primary_cause: PrimaryCause | null;
  drill_downs: DrillDown[];
  period: string;
  generated_by: 'ollama' | 'template' | 'error';
  message?: string;
}
