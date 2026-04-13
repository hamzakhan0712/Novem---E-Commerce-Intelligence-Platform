import ReactECharts from 'echarts-for-react';

import { CHART_COLORS } from '@/constants/theme';
import type { ChannelPerformance } from '@/types/marketing';

import styles from './ChannelRoasChart.module.css';

interface ChannelRoasChartProps {
  data: ChannelPerformance[];
}

const CHANNEL_LABELS: Record<string, string> = {
  google_ads: 'Google Ads',
  meta_ads: 'Meta Ads',
  tiktok: 'TikTok',
  email: 'Email',
  affiliate: 'Affiliate',
};

export default function ChannelRoasChart({ data }: ChannelRoasChartProps) {
  if (!data.length) return null;

  const sorted = [...data].sort((a, b) => b.roas - a.roas);
  const channels = sorted.map((d) => CHANNEL_LABELS[d.channel] || d.channel);
  const roasValues = sorted.map((d) => d.roas);

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Array<{ value: number; name: string }>) => {
        const p = params[0];
        return `<strong>${p.name}</strong><br/>ROAS: ${p.value.toFixed(2)}×`;
      },
    },
    grid: { left: 100, right: 40, top: 20, bottom: 20 },
    xAxis: {
      type: 'value' as const,
      name: 'ROAS',
      nameLocation: 'end' as const,
      axisLabel: { formatter: (v: number) => `${v}×` },
    },
    yAxis: {
      type: 'category' as const,
      data: channels,
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: roasValues.map((v) => ({
          value: v,
          itemStyle: { color: v >= 1 ? CHART_COLORS[0] : CHART_COLORS[7], borderRadius: [0, 4, 4, 0] },
        })),
        barMaxWidth: 28,
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed' as const, color: '#999' },
          data: [{ xAxis: 1, label: { formatter: 'Break-even', position: 'end' as const } }],
        },
      },
    ],
  };

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>ROAS by Channel</h3>
      <ReactECharts option={option} style={{ height: 280 }} />
    </div>
  );
}
