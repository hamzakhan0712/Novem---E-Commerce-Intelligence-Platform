export interface ProductMetrics {
  products_sold: number;
  categories: number;
  total_units: number;
  total_revenue: number;
  avg_price: number;
}

export interface ProductChanges {
  products_sold: number;
  total_units: number;
  total_revenue: number;
  avg_price: number;
}

export interface ProductSummary {
  current: ProductMetrics;
  previous: ProductMetrics;
  changes: ProductChanges;
}

export interface TopProduct {
  product_id: string;
  product_name: string;
  category: string | null;
  total_units: number;
  total_revenue: number;
  avg_price: number;
  order_count: number;
  unique_buyers: number;
}

export interface CategoryBreakdown {
  category: string;
  product_count: number;
  total_units: number;
  total_revenue: number;
  percentage: number;
  avg_price: number;
  unique_buyers: number;
}

export interface ProductTrendPoint {
  date: string;
  revenue: number;
  units: number;
  orders: number;
}

export type ProductPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';
export type ProductSort = 'revenue' | 'units';

// Market Basket Analysis (Apriori)
export interface BasketRule {
  if_bought: string;
  then_also_bought: string;
  support: number;
  confidence: number;
  lift: number;
  conviction: number;
  order_count: number;
}

export interface FrequentPair {
  products: string[];
  support: number;
  order_count: number;
}

export interface BasketAnalysis {
  model: string;
  rules: BasketRule[];
  frequent_pairs: FrequentPair[];
  total_orders: number;
  total_products: number;
  summary: Record<string, unknown>;
  message?: string;
}

// Inventory Optimization
export interface InventoryProduct {
  product_id: string;
  product_name: string;
  category: string;
  avg_daily_demand: number;
  std_daily_demand: number;
  total_units_sold: number;
  selling_days: number;
  lead_time_days: number;
  safety_stock: number;
  reorder_point: number;
  economic_order_qty: number;
  current_stock: number;
  days_of_stock: number;
  has_stock_data: boolean;
  status: 'critical' | 'reorder_now' | 'healthy' | 'overstocked' | 'no_data';
}

export interface InventorySummary {
  total_products: number;
  needs_reorder: number;
  overstocked: number;
  healthy: number;
  no_stock_data: number;
}

export interface InventoryAnalysis {
  products: InventoryProduct[];
  summary: InventorySummary;
  service_level: number;
  period: string;
  message?: string;
}

// Product Lifecycle (Dead Weight Detector)
export type LifecycleStage = 'rising_star' | 'cash_cow' | 'fading_out' | 'dead_weight';

export interface LifecycleProduct {
  product_id: string;
  product_name: string;
  category: string;
  lifecycle_stage: LifecycleStage;
  revenue_trend: number;
  velocity_score: number;
  sentiment_score: number;
  total_revenue: number;
  recent_revenue: number;
  order_count: number;
  recommendation: string;
}

export interface LifecycleSummary {
  rising_star: number;
  cash_cow: number;
  fading_out: number;
  dead_weight: number;
}

export interface ProductLifecycle {
  products: LifecycleProduct[];
  summary: LifecycleSummary;
  period: string;
  total_products: number;
  message?: string;
}

// Stock Forecast
export type StockUrgency = 'stockout_imminent' | 'low_stock' | 'adequate' | 'well_stocked';

export interface StockForecastProduct {
  product_id: string;
  product_name: string;
  category: string;
  current_stock: number;
  avg_daily_demand: number;
  days_until_stockout: number;
  predicted_stockout_date: string | null;
  urgency: StockUrgency;
}

export interface StockForecastSummary {
  total_products: number;
  stockout_imminent: number;
  low_stock: number;
  adequate: number;
  well_stocked: number;
}

export interface StockForecastData {
  products: StockForecastProduct[];
  summary: StockForecastSummary;
  period: string;
  message?: string;
}

// Stockout Impact
export interface StockoutEvent {
  product_id: string;
  product_name: string;
  category: string;
  stockout_snapshots: number;
  stockout_start: string;
  stockout_end: string;
  stockout_days: number;
  avg_daily_revenue: number;
  estimated_missed_revenue: number;
}

export interface StockoutImpactData {
  events: StockoutEvent[];
  total_estimated_loss: number;
  total_stockout_days: number;
  products_affected: number;
  period: string;
  message?: string;
}
