import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  CalendarOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';

import { formatCurrency } from '@/utils/formatCurrency';

import type { ForecastSummary, ForecastMetric } from '@/types/forecasting';

import styles from './ForecastStats.module.css';

interface Props {
  summary: ForecastSummary;
  metric: ForecastMetric;
  method: string;
}

function formatValue(val: number, metric: string): string {
  if (metric === 'revenue' || metric === 'aov') {
    return formatCurrency(val);
  }
  return val.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function TrendArrow({ value }: { value: number }) {
  const isUp = value > 0;
  const isDown = value < 0;
  const cls = isUp ? styles.changeUp : isDown ? styles.changeDown : styles.changeNeutral;

  return (
    <span className={`${styles.change} ${cls}`}>
      {isUp ? <ArrowUpOutlined /> : isDown ? <ArrowDownOutlined /> : <MinusOutlined />}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

export default function ForecastStats({ summary, metric, method }: Props) {
  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <span className={styles.label}>
          Historical Avg (Daily)
          <Tooltip title="Average daily value from your past order data">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatValue(summary.historical_avg, metric)}</span>
        </div>
        <span className={styles.sub}>
          <DatabaseOutlined /> {summary.data_points} days of data
        </span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Forecast Avg (Daily)
          <Tooltip title="Predicted average daily value over the forecast horizon">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatValue(summary.forecast_avg, metric)}</span>
          <TrendArrow value={summary.change_pct} />
        </div>
        <span className={styles.sub}>next {summary.horizon_days} days</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Forecast Total
          <Tooltip title="Sum of all predicted daily values over the forecast horizon">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatValue(summary.forecast_total, metric)}</span>
        </div>
        <span className={styles.sub}>
          {summary.horizon_days}-day projection
        </span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Peak Forecast Day
          <Tooltip title="Day with the highest predicted value in the forecast period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>
            {summary.peak_date
              ? formatValue(summary.peak_value, metric)
              : '—'}
          </span>
        </div>
        <span className={styles.sub}>
          {summary.peak_date ? (
            <><CalendarOutlined /> {summary.peak_date}</>
          ) : (
            'No forecast data'
          )}
        </span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Min Forecast Day
          <Tooltip title="Day with the lowest predicted value in the forecast period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>
            {summary.min_date
              ? formatValue(summary.min_value, metric)
              : '—'}
          </span>
        </div>
        <span className={styles.sub}>
          {summary.min_date ? (
            <><CalendarOutlined /> {summary.min_date}</>
          ) : (
            'No forecast data'
          )}
        </span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Method</span>
        <div className={styles.valueRow}>
          <span className={styles.value}>
            {method.replace('_', ' ')}
          </span>
        </div>
        <span className={styles.sub}>
          Trend: <strong style={{ textTransform: 'capitalize' }}>{summary.trend}</strong>
        </span>
      </div>
    </div>
  );
}
