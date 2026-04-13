import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';
import type { SentimentDistribution as DistributionData } from '@/types/sentiment';

import styles from './SentimentDistribution.module.css';

interface Props {
  distribution: DistributionData;
}

export default function SentimentDistribution({ distribution }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? 'rgba(255,255,255,0.58)' : 'rgba(0,0,0,0.55)';

  const total = distribution.positive + distribution.neutral + distribution.negative;

  if (total === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Review Breakdown</div>
        <div className={styles.emptyWrap}>
          <Empty description="No sentiment data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: { name: string; value: number; percent: number; marker: string }) =>
        `${params.marker} ${params.name}: <strong>${params.value.toLocaleString()}</strong> (${params.percent.toFixed(1)}%)`,
    },
    legend: {
      bottom: 0,
      textStyle: { color: textColor, fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          color: textColor,
          fontSize: 11,
          formatter: '{b}: {d}%',
        },
        data: [
          { value: distribution.positive, name: 'Positive', itemStyle: { color: '#52c41a' } },
          { value: distribution.neutral, name: 'Neutral', itemStyle: { color: '#faad14' } },
          { value: distribution.negative, name: 'Negative', itemStyle: { color: '#ff4d4f' } },
        ],
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Review Breakdown</div>
      <ReactECharts option={option} style={{ height: 280 }} notMerge />
    </div>
  );
}
