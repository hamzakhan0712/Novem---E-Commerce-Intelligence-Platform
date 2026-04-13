import { useState, useEffect } from 'react';

import { Segmented, Spin, Alert, Tabs } from 'antd';

import { useCustomerData } from '@/hooks/useCustomerData';
import { markPageVisited } from '@/components/dashboard/GettingStartedChecklist';
import { DataGate } from '@/components/shared';
import CustomerStats from '@/components/customers/CustomerStats';
import CustomerTable from '@/components/customers/CustomerTable';
import SegmentChart from '@/components/customers/SegmentChart';
import CustomerGrowthChart from '@/components/customers/CustomerGrowthChart';
import ChurnRiskPanel from '@/components/customers/ChurnRiskPanel';
import CohortReplayPanel from '@/components/customers/CohortReplayPanel';
import RetentionCurveCard from '@/components/customers/RetentionCurveCard';

import type { CustomerPeriod } from '@/types/customers';

import styles from './Customers.module.css';

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '14 days', value: '14d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
  { label: '6 months', value: '6m' },
  { label: '12 months', value: '12m' },
];

export default function Customers() {
  const { period, summary, topCustomers, segments, growth, churn, cohortReplay, loading, error, setPeriod, fetchCohortReplay, storeId } = useCustomerData();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => { markPageVisited('customers'); }, []);

  if (loading && !summary) {
    return (
      <DataGate pageKey="customers" className={styles.page}>
        <div className={styles.page}>
          <div className={styles.loadingCenter}>
            <Spin size="large" />
          </div>
        </div>
      </DataGate>
    );
  }

  return (
    <DataGate pageKey="customers" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Customers</h1>
          <span className={styles.subtitle}>Understand who your customers are and how they shop</span>
        </div>
        <Segmented options={PERIOD_OPTIONS} value={period} onChange={(v) => setPeriod(v as CustomerPeriod)} />
      </div>

      {error && (
        <Alert type="warning" message={error} showIcon closable />
      )}

      <Spin spinning={loading && !summary}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: 'Overview',
              children: (
                <div className={styles.content}>
                  {summary && <CustomerStats summary={summary} />}
                  <div className={styles.chartsRow}>
                    <SegmentChart segments={segments} />
                    <CustomerGrowthChart data={growth} />
                  </div>
                  <CustomerTable customers={topCustomers} loading={loading} />
                </div>
              ),
            },
            {
              key: 'churn',
              label: 'At-Risk Customers',
              children: (
                <div className={styles.content}>
                  <ChurnRiskPanel data={churn} />
                </div>
              ),
            },
            {
              key: 'cohort',
              label: 'Repeat Purchase Timeline',
              children: (
                <div className={styles.content}>
                  <CohortReplayPanel
                    data={cohortReplay}
                    onReplayChange={(month) => storeId && fetchCohortReplay(storeId, month || undefined)}
                  />
                  <RetentionCurveCard />
                </div>
              ),
            },
          ]}
        />
      </Spin>
    </div>
    </DataGate>
  );
}
