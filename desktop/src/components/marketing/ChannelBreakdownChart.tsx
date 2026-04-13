import ReactECharts from 'echarts-for-react';

import { CHART_COLORS } from '@/constants/theme';
import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';
import type { ChannelPerformance } from '@/types/marketing';

import styles from './ChannelBreakdownChart.module.css';

interface ChannelBreakdownChartProps {
  data: ChannelPerformance[];
}

const CHANNEL_LABELS: Record<string, string> = {
  google_ads: 'Google Ads',
  meta_ads: 'Meta Ads',
  tiktok: 'TikTok',
  email: 'Email',
  affiliate: 'Affiliate',
};

export default function ChannelBreakdownChart({ data }: ChannelBreakdownChartProps) {
  if (!data.length) return null;

  const channels = data.map((d) => CHANNEL_LABELS[d.channel] || d.channel);
  const spendValues = data.map((d) => d.spend);
  const revenueValues = data.map((d) => d.revenue);

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: Array<{ seriesName: string; value: number; axisValue: string }>) => {
        const title = params[0]?.axisValue || '';
        const lines = params.map(
          (p) => `${p.seriesName}: ${formatCurrency(p.value)}`
        );
        return `<strong>${title}</strong><br/>${lines.join('<br/>')}`;
      },
    },
    legend: { data: ['Spend', 'Revenue'], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: channels,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: {
        formatter: (v: number) => formatCurrencyCompact(v),
      },
    },
    series: [
      {
        name: 'Spend',
        type: 'bar',
        data: spendValues,
        itemStyle: { color: CHART_COLORS[7], borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
      {
        name: 'Revenue',
        type: 'bar',
        data: revenueValues,
        itemStyle: { color: CHART_COLORS[0], borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
    ],
  };

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>Spend vs Revenue by Channel</h3>
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
