export interface Alert {
  id: string;
  store_id: string | null;
  module: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertsPage {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
}
