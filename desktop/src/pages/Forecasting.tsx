import { useEffect } from 'react';

import { Segmented, Spin, Alert } from 'antd';

import { useForecastData } from '@/hooks/useForecastData';
import { useForecastStore } from '@/stores/forecastStore';
import { markPageVisited } from '@/components/dashboard/GettingStartedChecklist';
import { DataGate } from '@/components/shared';
import type { ForecastMetric } from '@/types/forecasting';

import { ForecastStats, ForecastChart, ForecastTable } from '@/components/forecasting';

import styles from './Forecasting.module.css';

const METRIC_OPTIONS = [
  { value: 'revenue', label: 'Revenue' },
  { value: 'orders', label: 'Orders' },
  { value: 'customers', label: 'Customers' },
  { value: 'aov', label: 'Avg. Order Value' },
];

const HORIZON_OPTIONS = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 60, label: '60 days' },
  { value: 90, label: '90 days' },
];

export default function Forecasting() {
  const { forecast, loading, error } = useForecastData();
  const metric = useForecastStore((s) => s.metric);
  const horizonDays = useForecastStore((s) => s.horizonDays);

  useEffect(() => { markPageVisited('forecasting'); }, []);
  const setMetric = useForecastStore((s) => s.setMetric);
  const setHorizonDays = useForecastStore((s) => s.setHorizonDays);

  const hasInsufficientData = forecast?.method === 'insufficient_data';

  return (
    <DataGate pageKey="forecasting" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Forecasting</h1>
          <span className={styles.subtitle}>Smart predictions for your store metrics</span>
        </div>
        <div className={styles.headerRight}>
          <Segmented
            value={metric}
            onChange={(val) => setMetric(val as ForecastMetric)}
            options={METRIC_OPTIONS}
          />
          <Segmented
            value={horizonDays}
            onChange={(val) => setHorizonDays(val as number)}
            options={HORIZON_OPTIONS}
          />
        </div>
      </div>

      {error && (
        <Alert
          type="error"
          message="Forecast Error"
          description={error}
          showIcon
          closable
        />
      )}

      {hasInsufficientData && (
        <Alert
          type="warning"
          message="Not Enough Data"
          description={forecast?.summary.message ?? 'Need at least 14 days of order data to generate predictions.'}
          showIcon
        />
      )}

      {forecast && !hasInsufficientData && (
        <>
          <ForecastStats summary={forecast.summary} metric={metric} method={forecast.method} />

          <ForecastChart
            data={forecast.data}
            metric={metric}
            method={forecast.method}
            horizonDays={forecast.horizon_days}
          />

          <ForecastTable data={forecast.data} metric={metric} />
        </>
      )}

      {!forecast && !loading && !error && (
        <div className={styles.loadingCenter}>
          <Spin size="large" />
        </div>
      )}
    </div>
    </DataGate>
  );
}
