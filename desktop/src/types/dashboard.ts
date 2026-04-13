export interface KpiValue {
  revenue: number;
  order_count: number;
  unique_customers: number;
  aov: number;
}

export interface KpiChanges {
  revenue: number | null;
  order_count: number | null;
  unique_customers: number | null;
  aov: number | null;
}

export interface KpiData {
  period: string;
  current: KpiValue;
  previous: KpiValue;
  changes: KpiChanges;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface DashboardSummary {
  kpis: KpiData;
  trends: TrendPoint[];
}

export type DashboardPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';
export type DashboardMetric = 'revenue' | 'orders' | 'customers' | 'aov';
export type DashboardGranularity = 'daily' | 'weekly' | 'monthly';

// Revenue At Risk
export interface AtRiskCustomer {
  customer_id: string;
  visit_count: number;
  avg_gap_days: number;
  days_since_last: number;
  days_overdue: number;
  historical_aov: number;
  total_spend: number;
  estimated_loss: number;
}

export interface RevenueAtRisk {
  total_at_risk: number;
  customers_at_risk: number;
  total_customers_analyzed: number;
  avg_days_overdue: number;
  lookahead_days: number;
  period: string;
  top_at_risk_customers: AtRiskCustomer[];
  message?: string;
}
