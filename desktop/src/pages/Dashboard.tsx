import { useEffect } from 'react';

import { Alert, Segmented, Spin } from 'antd';

import { useDashboardData } from '@/hooks/useDashboardData';
import { useDataQuality } from '@/hooks/useDataQuality';
import { useDashboardStore } from '@/stores/dashboardStore';
import KpiCard from '@/components/dashboard/KpiCard';
import TrendChart from '@/components/dashboard/TrendChart';
import DataQualityCard from '@/components/dashboard/DataQualityCard';
import RevenueAtRiskCard from '@/components/dashboard/RevenueAtRiskCard';
import TopProductsCard from '@/components/dashboard/TopProductsCard';
import QuickInsightsCard from '@/components/dashboard/QuickInsightsCard';
import GettingStartedChecklist, { markPageVisited } from '@/components/dashboard/GettingStartedChecklist';
import { DataGate } from '@/components/shared';
import ExportButton from '@/components/shared/ExportButton';
import { formatCurrency } from '@/utils/formatCurrency';
import type { DashboardPeriod } from '@/types/dashboard';

import styles from './Dashboard.module.css';

const PERIOD_OPTIONS = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: '12m', label: '12 months' },
];

function formatNumber(value: number): string {
  return (value ?? 0).toLocaleString();
}

export default function Dashboard() {
  const { kpis, trends, revenueAtRisk, loading } = useDashboardData();
  const { quality } = useDataQuality();
  const period = useDashboardStore((s) => s.period);
  const setPeriod = useDashboardStore((s) => s.setPeriod);

  useEffect(() => {
    markPageVisited('dashboard');
  }, []);

  if (loading && !kpis) {
    return (
      <DataGate pageKey="dashboard" className={styles.page}>
        <div className={styles.page}>
          <div className={styles.loadingCenter}>
            <Spin size="large" />
          </div>
        </div>
      </DataGate>
    );
  }

  const { current, changes, previous } = kpis ?? { current: {} as Record<string, number>, changes: {} as Record<string, number>, previous: {} as Record<string, number> };

  return (
    <DataGate pageKey="dashboard" className={styles.page}>
      <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Dashboard</h1>
          <span className={styles.subtitle}>Your store performance at a glance</span>
        </div>
        <div className={styles.headerRight}>
          <ExportButton />
          <Segmented
            value={period}
            onChange={(val) => setPeriod(val as DashboardPeriod)}
            options={PERIOD_OPTIONS}
          />
        </div>
      </div>

      {quality && quality.overall_score < 50 && (
        <Alert
          type="warning"
          showIcon
          closable
          message="Low Data Quality Detected"
          description={`Your data quality score is ${quality.overall_score}/100 (${quality.grade}). Some metrics may be inaccurate. Check the Data Quality card below for details.`}
          style={{ marginBottom: 16 }}
        />
      )}

      <GettingStartedChecklist />

      <div className={styles.kpiGrid}>
        <KpiCard
          label="Revenue"
          value={formatCurrency(current.revenue)}
          change={changes.revenue}
          previousValue={formatCurrency(previous.revenue)}
          tooltip="Net revenue (total price minus discounts) from completed orders only"
        />
        <KpiCard
          label="Orders"
          value={formatNumber(current.order_count)}
          change={changes.order_count}
          previousValue={formatNumber(previous.order_count)}
          tooltip="Count of completed orders in the selected period"
        />
        <KpiCard
          label="Customers"
          value={formatNumber(current.unique_customers)}
          change={changes.unique_customers}
          previousValue={formatNumber(previous.unique_customers)}
          tooltip="Unique customers who placed at least one completed order"
        />
        <KpiCard
          label="Avg. Order Value"
          value={formatCurrency(current.aov)}
          change={changes.aov}
          previousValue={formatCurrency(previous.aov)}
          tooltip="Net revenue divided by number of completed orders"
        />
      </div>

      <TrendChart data={trends} />

      <div className={styles.bottomGrid}>
        <TopProductsCard />
        <QuickInsightsCard />
      </div>

      <RevenueAtRiskCard data={revenueAtRisk} />

      <DataQualityCard />
    </div>
    </DataGate>
  );
}
