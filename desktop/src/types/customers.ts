export interface CustomerMetrics {
  total_customers: number;
  one_time_customers: number;
  returning_customers: number;
  returning_rate: number;
  total_spend: number;
  avg_lifetime_value: number;
}

export interface CustomerChanges {
  total_customers: number;
  returning_rate: number;
  total_spend: number;
  avg_lifetime_value: number;
}

export interface CustomerSummary {
  current: CustomerMetrics;
  previous: CustomerMetrics;
  changes: CustomerChanges;
}

export interface TopCustomer {
  customer_id: string;
  order_count: number;
  total_spend: number;
  first_order: string | null;
  last_order: string | null;
  avg_order_value: number;
}

export interface CustomerSegment {
  segment: string;
  count: number;
  percentage: number;
  total_spend: number;
  avg_spend: number;
}

export interface CustomerGrowthPoint {
  date: string;
  total: number;
  new_customers: number;
  returning_customers: number;
}

export type CustomerPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';

// Churn Prediction (BG/NBD model)
export interface ChurnCustomer {
  customer_id: string;
  p_alive: number;
  churn_risk: 'high' | 'medium' | 'low';
  predicted_purchases: number;
  frequency: number;
  recency_days: number;
  tenure_days: number;
  avg_order_value: number;
  expected_clv: number;
}

export interface ChurnSummary {
  total_scored: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  avg_alive_probability: number;
}

export interface ChurnPrediction {
  model: string;
  customers: ChurnCustomer[];
  summary: ChurnSummary;
  horizon_days: number;
  message?: string;
}

// Cohort Replay
export interface CohortMonth {
  month_index: number;
  retained_count: number;
  retention_pct: number;
  aov: number;
  revenue: number;
}

export interface CohortData {
  cohort_month: string;
  size: number;
  months: CohortMonth[];
}

export interface CohortReplay {
  replay_month: string | null;
  available_months: string[];
  cohorts: CohortData[];
  overall_retention: number[];
  summary: {
    total_cohorts: number;
    total_customers: number;
    avg_month0_retention?: number;
    avg_month1_retention?: number;
  };
  message?: string;
}
