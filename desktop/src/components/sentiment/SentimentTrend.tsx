import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';
import type { SentimentTrendPoint } from '@/types/sentiment';

import styles from './SentimentTrend.module.css';

interface Props {
  data: SentimentTrendPoint[];
}

export default function SentimentTrend({ data }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? 'rgba(255,255,255,0.58)' : 'rgba(0,0,0,0.55)';
  const borderColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

  if (data.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Review Sentiment Over Time</div>
        <div className={styles.emptyWrap}>
          <Empty description="No trend data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Array<{ seriesName: string; value: number; marker: string; dataIndex: number }>) => {
        const idx = params[0]?.dataIndex ?? 0;
        const point = data[idx];
        if (!point) return '';
        let html = `<strong>${point.date}</strong><br/>`;
        for (const p of params) {
          const val = p.seriesName === 'Avg Score' ? `${(p.value * 100).toFixed(0)}%` : p.value.toLocaleString();
          html += `${p.marker} ${p.seriesName}: <strong>${val}</strong><br/>`;
        }
        return html;
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: textColor, fontSize: 11 },
    },
    grid: { top: 12, right: 16, bottom: 36, left: 16, containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: data.map((d) => d.date),
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
    yAxis: [
      {
        type: 'value' as const,
        name: 'Score',
        nameTextStyle: { color: textColor, fontSize: 11 },
        min: 0,
        max: 1,
        axisLabel: {
          color: textColor,
          fontSize: 11,
          formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: borderColor, type: 'dashed' as const } },
      },
      {
        type: 'value' as const,
        name: 'Reviews',
        nameTextStyle: { color: textColor, fontSize: 11 },
        axisLabel: { color: textColor, fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Avg Score',
        type: 'line',
        yAxisIndex: 0,
        data: data.map((d) => d.avg_score),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: '#1677ff' },
        itemStyle: { color: '#1677ff' },
        areaStyle: {
          color: isDark ? 'rgba(22,119,255,0.1)' : 'rgba(22,119,255,0.08)',
        },
      },
      {
        name: 'Reviews',
        type: 'bar',
        yAxisIndex: 1,
        data: data.map((d) => d.count),
        barWidth: '60%',
        itemStyle: {
          color: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)',
          borderRadius: [2, 2, 0, 0],
        },
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Review Sentiment Over Time</div>
      <ReactECharts option={option} style={{ height: 280 }} notMerge />
    </div>
  );
}
