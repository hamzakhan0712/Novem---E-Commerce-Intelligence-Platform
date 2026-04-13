export interface ForecastPoint {
  date: string;
  value: number;
  lower: number | null;
  upper: number | null;
  is_forecast: boolean;
}

export interface ForecastSummary {
  historical_avg: number;
  forecast_avg: number;
  change_pct: number;
  trend: string;
  horizon_days: number;
  data_points: number;
  forecast_total: number;
  peak_date: string | null;
  peak_value: number;
  min_date: string | null;
  min_value: number;
  message?: string;
}

export interface ForecastResponse {
  metric: string;
  horizon_days: number;
  method: string;
  data: ForecastPoint[];
  summary: ForecastSummary;
}

export type ForecastMetric = 'revenue' | 'orders' | 'customers' | 'aov';

export interface MetricOverviewItem {
  metric: string;
  label: string;
  method: string;
  historical_avg: number;
  forecast_avg: number;
  change_pct: number;
  trend: string;
  forecast_total: number;
}
