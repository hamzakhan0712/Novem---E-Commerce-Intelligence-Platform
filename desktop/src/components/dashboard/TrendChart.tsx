import ReactECharts from 'echarts-for-react';
import { Segmented } from 'antd';

import { useDashboardStore } from '@/stores/dashboardStore';
import { useAppStore } from '@/stores/appStore';
import type { TrendPoint, DashboardMetric, DashboardGranularity } from '@/types/dashboard';

import styles from './TrendChart.module.css';

const METRIC_LABELS: Record<DashboardMetric, string> = {
  revenue: 'Revenue',
  orders: 'Orders',
  customers: 'Customers',
  aov: 'Avg. Order Value',
};

const GRANULARITY_LABELS: Record<DashboardGranularity, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
};

interface TrendChartProps {
  data: TrendPoint[];
}

export default function TrendChart({ data }: TrendChartProps) {
  const metric = useDashboardStore((s) => s.metric);
  const granularity = useDashboardStore((s) => s.granularity);
  const setMetric = useDashboardStore((s) => s.setMetric);
  const setGranularity = useDashboardStore((s) => s.setGranularity);
  const themeMode = useAppStore((s) => s.themeMode);

  const isDark = themeMode === 'dark';
  const textColor = isDark ? 'rgba(255,255,255,0.58)' : 'rgba(0,0,0,0.55)';
  const gridLineColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? '#1a1a1a' : '#fff',
      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      textStyle: { color: isDark ? '#fff' : '#000', fontSize: 12 },
    },
    grid: { top: 12, right: 16, bottom: 28, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((p) => p.date.slice(0, 10)),
      axisLabel: { color: textColor, fontSize: 11 },
      axisLine: { lineStyle: { color: gridLineColor } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { lineStyle: { color: gridLineColor } },
    },
    series: [
      {
        type: 'line',
        data: data.map((p) => p.value),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#52c41a' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.25)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.02)' },
            ],
          },
        },
      },
    ],
  };

  return (
    <div className={styles.chartWrapper}>
      <div className={styles.chartHeader}>
        <h3 className={styles.chartTitle}>Trend</h3>
        <div className={styles.controls}>
          <Segmented
            size="small"
            value={metric}
            onChange={(val) => setMetric(val as DashboardMetric)}
            options={Object.entries(METRIC_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Segmented
            size="small"
            value={granularity}
            onChange={(val) => setGranularity(val as DashboardGranularity)}
            options={Object.entries(GRANULARITY_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
        </div>
      </div>
      <ReactECharts option={option} style={{ height: 320 }} notMerge lazyUpdate />
    </div>
  );
}
