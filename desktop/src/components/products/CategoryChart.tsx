import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';

import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';

import type { CategoryBreakdown } from '@/types/products';

import styles from './CategoryChart.module.css';

interface Props {
  categories: CategoryBreakdown[];
}

export default function CategoryChart({ categories }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const textColor = themeMode === 'dark' ? '#e0e0e0' : '#333';
  const gridColor = themeMode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';

  if (categories.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Revenue by Category</div>
        <div className={styles.emptyWrap}>
          <Empty description="No category data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const sorted = [...categories].sort((a, b) => b.total_revenue - a.total_revenue).slice(0, 10);

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: Array<{ name: string; value: number; marker: string }>) => {
        const cat = sorted.find((c) => c.category === params[0]?.name);
        if (!cat) return '';
        return `<strong>${cat.category}</strong><br/>
Revenue: <strong>${formatCurrency(cat.total_revenue)}</strong><br/>
Products: <strong>${cat.product_count}</strong><br/>
Units: <strong>${cat.total_units.toLocaleString()}</strong><br/>
Avg. Price: <strong>${formatCurrency(cat.avg_price)}</strong><br/>
Unique Buyers: <strong>${cat.unique_buyers.toLocaleString()}</strong>`;
      },
    },
    grid: { left: 120, right: 30, top: 10, bottom: 30 },
    xAxis: {
      type: 'value',
      axisLabel: {
        color: textColor,
        formatter: (v: number) => formatCurrencyCompact(v),
      },
      splitLine: { lineStyle: { color: gridColor } },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((c) => c.category),
      inverse: true,
      axisLabel: { color: textColor },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: sorted.map((c) => c.total_revenue),
        itemStyle: {
          color: '#52c41a',
          borderRadius: [0, 4, 4, 0],
        },
        barMaxWidth: 24,
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.titleRow}>
        <span className={styles.title}>Revenue by Category</span>
        <span className={styles.subtitle}>{categories.length} categories</span>
      </div>
      <ReactECharts option={option} className={styles.chart} />
    </div>
  );
}
