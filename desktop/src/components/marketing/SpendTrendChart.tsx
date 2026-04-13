import { useMemo } from 'react';

import { Segmented } from 'antd';
import ReactECharts from 'echarts-for-react';

import { CHART_COLORS } from '@/constants/theme';
import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';
import type { ChannelTrendPoint, MarketingGranularity } from '@/types/marketing';

import styles from './SpendTrendChart.module.css';

interface SpendTrendChartProps {
  data: ChannelTrendPoint[];
  granularity: MarketingGranularity;
  onGranularityChange: (g: MarketingGranularity) => void;
}

const CHANNEL_COLORS: Record<string, string> = {
  google_ads: CHART_COLORS[1],
  meta_ads: CHART_COLORS[2],
  tiktok: CHART_COLORS[3],
  email: CHART_COLORS[4],
  affiliate: CHART_COLORS[5],
};

const CHANNEL_LABELS: Record<string, string> = {
  google_ads: 'Google Ads',
  meta_ads: 'Meta Ads',
  tiktok: 'TikTok',
  email: 'Email',
  affiliate: 'Affiliate',
};

const GRANULARITY_OPTIONS = [
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' },
];

export default function SpendTrendChart({ data, granularity, onGranularityChange }: SpendTrendChartProps) {
  const { dates, series } = useMemo(() => {
    if (!data.length) return { dates: [], series: [] };

    const channelMap = new Map<string, Map<string, number>>();
    const dateSet = new Set<string>();

    for (const pt of data) {
      dateSet.add(pt.date);
      if (!channelMap.has(pt.channel)) channelMap.set(pt.channel, new Map());
      channelMap.get(pt.channel)!.set(pt.date, pt.spend);
    }

    const sortedDates = Array.from(dateSet).sort();
    const s = Array.from(channelMap.entries()).map(([channel, dateMap]) => ({
      name: CHANNEL_LABELS[channel] || channel,
      type: 'line' as const,
      stack: 'Total',
      areaStyle: { opacity: 0.3 },
      smooth: true,
      symbol: 'none',
      itemStyle: { color: CHANNEL_COLORS[channel] || '#999' },
      data: sortedDates.map((d) => dateMap.get(d) || 0),
    }));

    return { dates: sortedDates, series: s };
  }, [data]);

  if (!data.length) return null;

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Array<{ seriesName: string; value: number }>) => {
        const lines = params
          .filter((p) => p.value > 0)
          .map((p) => `${p.seriesName}: ${formatCurrency(p.value)}`);
        return lines.join('<br/>');
      },
    },
    legend: { bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: dates,
      axisLabel: { fontSize: 10, rotate: dates.length > 30 ? 45 : 0 },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: {
        formatter: (v: number) => formatCurrencyCompact(v),
      },
    },
    series,
  };

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>Spend Trend</h3>
        <Segmented
          size="small"
          options={GRANULARITY_OPTIONS}
          value={granularity}
          onChange={(v) => onGranularityChange(v as MarketingGranularity)}
        />
      </div>
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
