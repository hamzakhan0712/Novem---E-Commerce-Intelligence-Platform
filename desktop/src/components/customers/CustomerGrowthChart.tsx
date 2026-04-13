import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';

import type { CustomerGrowthPoint } from '@/types/customers';

import styles from './CustomerGrowthChart.module.css';

interface Props {
  data: CustomerGrowthPoint[];
}

export default function CustomerGrowthChart({ data }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#333';
  const borderColor = isDark ? '#303030' : '#e8e8e8';

  if (data.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Customer Growth</div>
        <div className={styles.emptyWrap}>
          <Empty description="No growth data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
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
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { lineStyle: { color: borderColor, type: 'dashed' } },
    },
    series: [
      {
        name: 'New Customers',
        type: 'bar',
        stack: 'customers',
        data: data.map((d) => d.new_customers),
        itemStyle: { color: '#1890ff', borderRadius: [0, 0, 0, 0] },
        barMaxWidth: 24,
      },
      {
        name: 'Returning Customers',
        type: 'bar',
        stack: 'customers',
        data: data.map((d) => d.returning_customers),
        itemStyle: { color: '#52c41a', borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 24,
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Customer Growth</div>
      <ReactECharts option={option} className={styles.chart} />
    </div>
  );
}
