export type MarketingPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';
export type MarketingGranularity = 'daily' | 'weekly' | 'monthly';
export type CampaignSortField = 'roas' | 'spend' | 'conversions' | 'revenue' | 'cpc' | 'ctr';

export interface MarketingKpis {
  total_spend: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_revenue: number;
  roas: number;
  avg_cpc: number;
  avg_ctr: number;
  avg_cvr: number;
  cpa: number;
}

export interface MarketingKpiChanges {
  total_spend: number;
  total_revenue: number;
  roas: number;
  avg_cpc: number;
  avg_ctr: number;
  avg_cvr: number;
  cpa: number;
  total_conversions: number;
}

export interface MarketingKpiResponse {
  period: string;
  current: MarketingKpis;
  previous: MarketingKpis;
  changes: MarketingKpiChanges;
}

export interface ChannelPerformance {
  channel: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
  roas: number;
  cpc: number;
  ctr: number;
  cvr: number;
}

export interface ChannelTrendPoint {
  date: string;
  channel: string;
  spend: number;
  revenue: number;
  roas: number;
  conversions: number;
  impressions: number;
  clicks: number;
  ctr: number;
}

export interface CampaignPerformance {
  channel: string;
  campaign_name: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
  roas: number;
  cpc: number;
  ctr: number;
  cvr: number;
  active_days: number;
}

// Phase 3 cross-correlation types
export interface WastedSpendAlert {
  campaign_name: string;
  channel: string;
  category: string;
  spend: number;
  revenue: number;
  roas: number;
  out_of_stock_products: string[];
  reason: string;
}

export interface WastedSpendData {
  alerts: WastedSpendAlert[];
  total_wasted_spend: number;
  total_campaigns_flagged: number;
  message: string;
}

export interface CategoryRoi {
  category: string;
  ad_spend: number;
  ad_attributed_revenue: number;
  order_revenue: number;
  order_count: number;
  roas: number | null;
}
