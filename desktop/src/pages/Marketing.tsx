import { useState } from 'react';

import { Segmented, Spin, Alert, Tabs } from 'antd';

import { useMarketingData } from '@/hooks/useMarketingData';
import { DataGate } from '@/components/shared';
import MarketingKpiCards from '@/components/marketing/MarketingKpiCards';
import ChannelRoasChart from '@/components/marketing/ChannelRoasChart';
import SpendTrendChart from '@/components/marketing/SpendTrendChart';
import ChannelBreakdownChart from '@/components/marketing/ChannelBreakdownChart';
import CampaignTable from '@/components/marketing/CampaignTable';
import WastedSpendAlert from '@/components/marketing/WastedSpendAlert';
import CategoryRoiChart from '@/components/marketing/CategoryRoiChart';

import type { MarketingPeriod } from '@/types/marketing';

import styles from './Marketing.module.css';

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '14 days', value: '14d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
  { label: '6 months', value: '6m' },
  { label: '12 months', value: '12m' },
];

export default function Marketing() {
  const {
    period, granularity, campaignSort,
    kpis, channels, trends, campaigns,
    wastedSpend, categoryRoi,
    loading, error,
    setPeriod, setGranularity, setCampaignSort,
  } = useMarketingData();
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <DataGate pageKey="marketing" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Marketing</h1>
          <span className={styles.subtitle}>Track ad performance, channel efficiency, and campaign ROI</span>
        </div>
        <Segmented options={PERIOD_OPTIONS} value={period} onChange={(v) => setPeriod(v as MarketingPeriod)} />
      </div>

      {error && <Alert type="error" message={error} showIcon closable />}

      {loading && !kpis ? (
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
                  <WastedSpendAlert data={wastedSpend} />
                  {kpis && <MarketingKpiCards data={kpis} />}
                  <div className={styles.chartsRow}>
                    <ChannelRoasChart data={channels} />
                    <SpendTrendChart data={trends} granularity={granularity} onGranularityChange={setGranularity} />
                  </div>
                  <CategoryRoiChart data={categoryRoi} />
                </div>
              ),
            },
            {
              key: 'campaigns',
              label: 'Campaigns',
              children: (
                <div className={styles.content}>
                  <ChannelBreakdownChart data={channels} />
                  <CampaignTable data={campaigns} sortBy={campaignSort} onSortChange={setCampaignSort} />
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
