import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';
import type { ForecastPoint, ForecastMetric } from '@/types/forecasting';

import styles from './ForecastChart.module.css';

interface Props {
  data: ForecastPoint[];
  metric: ForecastMetric;
  method: string;
  horizonDays: number;
}

import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';

function formatAxisValue(val: number, metric: string): string {
  if (metric === 'revenue' || metric === 'aov') {
    return formatCurrencyCompact(val);
  }
  if (val >= 1000) return `${(val / 1000).toFixed(1)}k`;
  return val.toFixed(0);
}

function formatTooltipValue(val: number, metric: string): string {
  if (metric === 'revenue' || metric === 'aov') {
    return formatCurrency(val);
  }
  return val.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

const METRIC_LABELS: Record<string, string> = {
  revenue: 'Revenue',
  orders: 'Orders',
  customers: 'Customers',
  aov: 'Avg Order Value',
};

export default function ForecastChart({ data, metric, method, horizonDays }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? 'rgba(255,255,255,0.58)' : 'rgba(0,0,0,0.55)';
  const borderColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

  if (data.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.header}>
          <span className={styles.title}>Forecast</span>
        </div>
        <div className={styles.emptyWrap}>
          <Empty description="No forecast data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const historicalData = data.filter((p) => !p.is_forecast);
  const allDates = data.map((p) => p.date.slice(0, 10));

  // Find the boundary date between historical and forecast
  const boundaryIndex = historicalData.length > 0 ? historicalData.length - 1 : 0;
  const boundaryDate = allDates[boundaryIndex] ?? '';

  const metricLabel = METRIC_LABELS[metric] ?? metric;

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: isDark ? '#1a1a1a' : '#fff',
      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      textStyle: { color: isDark ? '#fff' : '#000', fontSize: 12 },
      formatter: (params: Array<{ seriesName: string; value: number | null; dataIndex: number; marker: string }>) => {
        const idx = params[0]?.dataIndex ?? 0;
        const point = data[idx];
        if (!point) return '';
        const dateStr = point.date;

        let html = `<strong>${dateStr}</strong><br/>`;
        const isFc = point.is_forecast;

        html += `${params[0]?.marker ?? ''} ${isFc ? 'Forecast' : 'Historical'}: <strong>${formatTooltipValue(point.value, metric)}</strong><br/>`;

        if (isFc && point.lower != null && point.upper != null) {
          html += `<span style="color:${textColor}">Range: ${formatTooltipValue(point.lower, metric)} — ${formatTooltipValue(point.upper, metric)}</span>`;
        }

        return html;
      },
    },
    legend: {
      data: ['Historical', 'Forecast'],
      textStyle: { color: textColor, fontSize: 11 },
      top: 0,
      right: 0,
    },
    grid: { top: 40, right: 16, bottom: 28, left: 16, containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: allDates,
      axisLabel: {
        color: textColor,
        fontSize: 11,
        formatter: (v: string) => {
          const d = new Date(v);
          return `${d.getMonth() + 1}/${d.getDate()}`;
        },
      },
      axisLine: { lineStyle: { color: borderColor } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value' as const,
      name: metricLabel,
      nameTextStyle: { color: textColor, fontSize: 11 },
      axisLabel: {
        color: textColor,
        fontSize: 11,
        formatter: (v: number) => formatAxisValue(v, metric),
      },
      splitLine: { lineStyle: { color: borderColor, type: 'dashed' as const } },
    },
    series: [
      // Historical line
      {
        name: 'Historical',
        type: 'line',
        data: data.map((p) => (p.is_forecast ? null : p.value)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1677ff' },
        itemStyle: { color: '#1677ff' },
        connectNulls: false,
      },
      // Forecast line — connect to last historical point for smooth transition
      {
        name: 'Forecast',
        type: 'line',
        data: data.map((p, i) => {
          if (p.is_forecast) return p.value;
          if (i === boundaryIndex) return p.value;
          return null;
        }),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, type: 'dashed' as const, color: '#722ed1' },
        itemStyle: { color: '#722ed1' },
        connectNulls: false,
      },
      // Confidence upper bound (invisible line, acts as stack base)
      {
        name: 'Upper',
        type: 'line',
        data: data.map((p) => (p.is_forecast && p.upper != null ? p.upper : null)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 0 },
        areaStyle: { color: 'transparent' },
        stack: 'confidence',
        silent: true,
      },
      // Confidence lower bound (shaded area between upper and lower)
      {
        name: 'Lower',
        type: 'line',
        data: data.map((p) => (p.is_forecast && p.lower != null ? p.lower : null)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 0 },
        areaStyle: {
          color: isDark ? 'rgba(114,46,209,0.15)' : 'rgba(114,46,209,0.1)',
        },
        stack: 'confidence',
        silent: true,
      },
    ],
    // Mark the forecast boundary
    ...(boundaryDate
      ? {
          visualMap: undefined,
        }
      : {}),
  };

  // Add markLine to the historical series
  if (boundaryDate) {
    (option.series[0] as Record<string, unknown>).markLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)', type: 'dashed', width: 1 },
      data: [{ xAxis: boundaryDate }],
      label: {
        show: true,
        position: 'insideEndTop',
        formatter: 'Forecast →',
        color: textColor,
        fontSize: 10,
      },
    };
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>{metricLabel} Forecast</span>
        <span className={styles.badge}>
          {method.replace('_', ' ')} · {horizonDays}-day horizon
        </span>
      </div>
      <ReactECharts option={option} style={{ height: 400 }} notMerge />
    </div>
  );
}
