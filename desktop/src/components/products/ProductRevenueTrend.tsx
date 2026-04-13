import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';

import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';

import type { ProductTrendPoint } from '@/types/products';

import styles from './ProductRevenueTrend.module.css';

interface Props {
  data: ProductTrendPoint[];
}

export default function ProductRevenueTrend({ data }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#333';
  const borderColor = isDark ? '#303030' : '#e8e8e8';

  if (data.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Revenue Trend</div>
        <div className={styles.emptyWrap}>
          <Empty description="No trend data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: Array<{ seriesName: string; value: number; marker: string }>) => {
        const idx = params[0] ? data.findIndex((d) => d.revenue === params[0].value || d.units === params[0].value || d.orders === params[0].value) : 0;
        const point = data[idx >= 0 ? idx : 0];
        let html = `<strong>${point?.date ?? ''}</strong><br/>`;
        for (const p of params) {
          html += `${p.marker} ${p.seriesName}: <strong>${
            p.seriesName === 'Revenue'
              ? formatCurrency(p.value)
              : p.value.toLocaleString()
          }</strong><br/>`;
        }
        return html;
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: textColor },
    },
    grid: {
      left: '3%',
      right: '3%',
      top: '10%',
      bottom: '18%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
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
        type: 'value',
        name: 'Revenue',
        nameTextStyle: { color: textColor, fontSize: 11 },
        axisLabel: {
          color: textColor,
          fontSize: 11,
          formatter: (v: number) => formatCurrencyCompact(v),
        },
        splitLine: { lineStyle: { color: borderColor, type: 'dashed' } },
      },
      {
        type: 'value',
        name: 'Units',
        nameTextStyle: { color: textColor, fontSize: 11 },
        axisLabel: { color: textColor, fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Revenue',
        type: 'line',
        data: data.map((d) => d.revenue),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#1890ff' },
        yAxisIndex: 0,
      },
      {
        name: 'Units',
        type: 'bar',
        data: data.map((d) => d.units),
        itemStyle: { color: '#52c41a', borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 18,
        yAxisIndex: 1,
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Revenue Trend</div>
      <ReactECharts option={option} className={styles.chart} />
    </div>
  );
}
