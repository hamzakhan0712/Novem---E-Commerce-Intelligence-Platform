import { useState, useEffect, useCallback } from 'react';

import { Empty, Spin } from 'antd';
import { ShoppingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';
import { formatCurrency } from '@/utils/formatCurrency';
import { ROUTES } from '@/constants/routes';

import styles from './TopProductsCard.module.css';

interface TopProduct {
  product_name: string;
  total_revenue: number;
  total_units: number;
  order_count: number;
}

export default function TopProductsCard() {
  const navigate = useNavigate();
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTop = useCallback(async () => {
    if (!activeStoreId) return;
    setLoading(true);
    try {
      const res = await apiClient.get(
        `/products/top?store_id=${encodeURIComponent(activeStoreId)}&limit=5&sort_by=revenue`,
      );
      setProducts(res.data?.data ?? []);
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [activeStoreId]);

  useEffect(() => {
    fetchTop();
  }, [fetchTop, lastSyncTick]);

  if (loading) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <ShoppingOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>Top Products</span>
        </div>
        <div className={styles.loadingCenter}><Spin size="small" /></div>
      </div>
    );
  }

  const maxRevenue = products.length > 0 ? products[0].total_revenue : 1;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <ShoppingOutlined className={styles.headerIcon} />
        <span className={styles.headerTitle}>Top Products</span>
        <button className={styles.viewAll} onClick={() => navigate(ROUTES.PRODUCTS)}>
          View all
        </button>
      </div>

      {products.length === 0 ? (
        <Empty description="No product data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className={styles.list}>
          {products.map((p, i) => (
            <div key={i} className={styles.row}>
              <span className={styles.rank}>{i + 1}</span>
              <div className={styles.productInfo}>
                <span className={styles.productName}>{p.product_name}</span>
                <div className={styles.bar}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(p.total_revenue / maxRevenue) * 100}%` }}
                  />
                </div>
              </div>
              <div className={styles.productStats}>
                <span className={styles.revenue}>{formatCurrency(p.total_revenue)}</span>
                <span className={styles.units}>{p.total_units} units</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
