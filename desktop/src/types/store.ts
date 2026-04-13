export interface Store {
  id: string;
  name: string;
  platform: string;
  url: string | null;
  currency: string;
  timezone: string;
  industry: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  data_summary: StoreDataCounts | null;
}

export interface StoreDataCounts {
  orders: number;
  customers: number;
  products: number;
  ad_spend: number;
  reviews: number;
  stock_levels: number;
  total_imports: number;
  last_import_at: string | null;
}

export interface CreateStoreRequest {
  name: string;
  platform: string;
  url?: string;
  currency?: string;
  timezone?: string;
  industry?: string;
  description?: string;
}

export interface UpdateStoreRequest {
  name?: string;
  platform?: string;
  url?: string;
  currency?: string;
  timezone?: string;
  industry?: string;
  description?: string;
}
