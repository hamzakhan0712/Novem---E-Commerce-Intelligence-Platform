import { useState } from 'react';

import { Spin, Segmented, Alert, Tabs } from 'antd';

import { useInsightData } from '@/hooks/useInsightData';
import { DataGate } from '@/components/shared';
import InsightSummary from '@/components/insights/InsightSummary';
import InsightList from '@/components/insights/InsightList';
import AnomalyList from '@/components/insights/AnomalyList';
import ActionList from '@/components/insights/ActionList';
import CausalBreakdownPanel from '@/components/insights/CausalBreakdownPanel';
import MissedRevenuePanel from '@/components/insights/MissedRevenuePanel';
import HealthScoreCard from '@/components/insights/HealthScoreCard';
import InsightFeed from '@/components/insights/InsightFeed';
import ShapExplainPanel from '@/components/insights/ShapExplainPanel';
import ScenarioSimulator from '@/components/insights/ScenarioSimulator';
import BusinessDnaRadar from '@/components/insights/BusinessDnaRadar';
import BenchmarkCard from '@/components/insights/BenchmarkCard';
import RootCauseCard from '@/components/insights/RootCauseCard';

import type { InsightPeriod } from '@/types/insights';

import styles from './Insights.module.css';

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '14 days', value: '14d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
  { label: '6 months', value: '6m' },
  { label: '12 months', value: '12m' },
];

export default function Insights() {
  const {
    period, insights, anomalies, actions, summary,
    drivers, missedRevenue, feed, healthScore, shap, scenario,
    businessDna, rootCause,
    loading, error, setPeriod, runScenario, storeId,
  } = useInsightData();
  const [activeTab, setActiveTab] = useState('feed');

  const tabItems = [
    {
      key: 'feed',
      label: 'Intelligence Feed',
      children: (
        <div className={styles.tabContent}>
          <div className={styles.topRow}>
            {healthScore && <HealthScoreCard score={healthScore} />}
            {summary && <InsightSummary summary={summary} />}
          </div>
          <InsightFeed feed={feed} />
          <RootCauseCard data={rootCause} />
        </div>
      ),
    },
    {
      key: 'dna',
      label: 'Store Profile',
      children: (
        <div className={styles.tabContent}>
          <BusinessDnaRadar data={businessDna} />
          <BenchmarkCard />
        </div>
      ),
    },
    {
      key: 'analysis',
      label: 'Deep Analysis',
      children: (
        <div className={styles.tabContent}>
          <div className={styles.analysisGrid}>
            <CausalBreakdownPanel breakdown={drivers} />
            <MissedRevenuePanel data={missedRevenue} />
          </div>
          <InsightList insights={insights} />
        </div>
      ),
    },
    {
      key: 'anomalies',
      label: 'Unusual Activity',
      children: (
        <div className={styles.tabContent}>
          <AnomalyList anomalies={anomalies} />
        </div>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      children: (
        <div className={styles.tabContent}>
          <ActionList actions={actions} />
        </div>
      ),
    },
    {
      key: 'explainability',
      label: 'Why It Happens',
      children: (
        <div className={styles.tabContent}>
          <ShapExplainPanel data={shap} />
        </div>
      ),
    },
    {
      key: 'whatif',
      label: 'What-If',
      children: (
        <div className={styles.tabContent}>
          <ScenarioSimulator
            scenario={scenario}
            loading={loading}
            onRun={(adj) => storeId && runScenario(storeId, adj)}
          />
        </div>
      ),
    },
  ];

  return (
    <DataGate pageKey="insights" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Insights</h1>
          <span className={styles.subtitle}>AI-powered analysis and recommendations for your business</span>
        </div>
        <Segmented options={PERIOD_OPTIONS} value={period} onChange={(v) => setPeriod(v as InsightPeriod)} />
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
          items={tabItems}
          className={styles.tabs}
        />
      )}
    </div>
    </DataGate>
  );
}
