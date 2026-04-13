import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';
import type { RatingBreakdown as RatingData } from '@/types/sentiment';

import styles from './RatingBreakdown.module.css';

interface Props {
  data: RatingData[];
}

export default function RatingBreakdown({ data }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? 'rgba(255,255,255,0.58)' : 'rgba(0,0,0,0.55)';
  const borderColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

  if (data.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Reviews by Rating</div>
        <div className={styles.emptyWrap}>
          <Empty description="No rating data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Array<{ dataIndex: number; marker: string }>) => {
        const idx = params[0]?.dataIndex ?? 0;
        const item = data[idx];
        if (!item) return '';
        return `${params[0]?.marker ?? ''} ${item.rating}★<br/>
          Reviews: <strong>${item.count.toLocaleString()}</strong><br/>
          Avg Sentiment: <strong>${(item.avg_sentiment * 100).toFixed(0)}%</strong>`;
      },
    },
    grid: { top: 8, right: 16, bottom: 28, left: 40 },
    xAxis: {
      type: 'category' as const,
      data: data.map((r) => `${r.rating}★`),
      axisLabel: { color: textColor, fontSize: 12 },
      axisLine: { lineStyle: { color: borderColor } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { lineStyle: { color: borderColor, type: 'dashed' as const } },
    },
    series: [
      {
        type: 'bar',
        data: data.map((r) => ({
          value: r.count,
          itemStyle: {
            color: r.avg_sentiment >= 0.6 ? '#52c41a' : r.avg_sentiment <= 0.4 ? '#ff4d4f' : '#faad14',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '50%',
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Reviews by Rating</div>
      <ReactECharts option={option} style={{ height: 280 }} notMerge />
    </div>
  );
}
