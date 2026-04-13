import { useState } from 'react';

import { Segmented, Spin, Alert, Tabs } from 'antd';

import { useProductData } from '@/hooks/useProductData';
import { DataGate } from '@/components/shared';
import ProductStats from '@/components/products/ProductStats';
import ProductTable from '@/components/products/ProductTable';
import CategoryChart from '@/components/products/CategoryChart';
import ProductRevenueTrend from '@/components/products/ProductRevenueTrend';
import BasketAnalysisPanel from '@/components/products/BasketAnalysisPanel';
import InventoryPanel from '@/components/products/InventoryPanel';
import LifecyclePanel from '@/components/products/LifecyclePanel';
import StockForecastPanel from '@/components/products/StockForecastPanel';
import StockoutImpactCard from '@/components/products/StockoutImpactCard';

import type { ProductPeriod } from '@/types/products';

import styles from './Products.module.css';

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '14 days', value: '14d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
  { label: '6 months', value: '6m' },
  { label: '12 months', value: '12m' },
];

export default function Products() {
  const { period, sortBy, summary, topProducts, categories, trend, basket, inventory, lifecycle, stockForecast, stockoutImpact, loading, error, setPeriod, setSortBy } = useProductData();
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <DataGate pageKey="products" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Products</h1>
          <span className={styles.subtitle}>See which products drive your revenue and how categories perform</span>
        </div>
        <Segmented options={PERIOD_OPTIONS} value={period} onChange={(v) => setPeriod(v as ProductPeriod)} />
      </div>

      {error && <Alert type="error" message={error} showIcon closable />}

      {loading && !summary ? (
        <div className={styles.loadingCenter}>
          <Spin size="large" />
        </div>
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: 'Overview',
              children: (
                <div className={styles.content}>
                  {summary && <ProductStats summary={summary} />}
                  <div className={styles.chartsRow}>
                    <CategoryChart categories={categories} />
                    <ProductRevenueTrend data={trend} />
                  </div>
                  <ProductTable products={topProducts} loading={loading} sortBy={sortBy} onSortChange={setSortBy} />
                </div>
              ),
            },
            {
              key: 'basket',
              label: 'Basket Analysis',
              children: (
                <div className={styles.content}>
                  <BasketAnalysisPanel data={basket} />
                </div>
              ),
            },
            {
              key: 'inventory',
              label: 'Inventory',
              children: (
                <div className={styles.content}>
                  <InventoryPanel data={inventory} />
                </div>
              ),
            },
            {
              key: 'lifecycle',
              label: 'Product Lifecycle',
              children: (
                <div className={styles.content}>
                  <LifecyclePanel data={lifecycle} />
                </div>
              ),
            },
            {
              key: 'stock-forecast',
              label: 'Stock Forecast',
              children: (
                <div className={styles.content}>
                  <StockForecastPanel data={stockForecast} />
                </div>
              ),
            },
            {
              key: 'stockout-impact',
              label: 'Stockout Impact',
              children: (
                <div className={styles.content}>
                  <StockoutImpactCard data={stockoutImpact} />
                </div>
              ),
            },
          ]}
        />
      )}
    </div>
    </DataGate>
  );
}
