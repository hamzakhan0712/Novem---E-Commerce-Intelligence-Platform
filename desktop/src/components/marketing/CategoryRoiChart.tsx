import { useMemo } from 'react';

import ReactECharts from 'echarts-for-react';

import { CHART_COLORS } from '@/constants/theme';
import { formatCurrency, formatCurrencyCompact } from '@/utils/formatCurrency';
import type { CategoryRoi } from '@/types/marketing';

import styles from './CategoryRoiChart.module.css';

interface CategoryRoiChartProps {
  data: CategoryRoi[];
}

export default function CategoryRoiChart({ data }: CategoryRoiChartProps) {
  const option = useMemo(() => {
    if (!data.length) return null;

    const categories = data.map((d) => d.category);
    const adSpend = data.map((d) => d.ad_spend);
    const orderRevenue = data.map((d) => d.order_revenue);

    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
        formatter: (params: Array<{ seriesName: string; value: number; marker: string; axisValueLabel: string }>) => {
          const cat = params[0]?.axisValueLabel || '';
          let html = `<b>${cat}</b><br/>`;
          for (const p of params) {
            html += `${p.marker} ${p.seriesName}: ${formatCurrency(p.value)}<br/>`;
          }
          const matched = data.find((d) => d.category === cat);
          if (matched?.roas != null) {
            html += `<br/>ROAS: <b>${matched.roas}×</b>`;
          }
          return html;
        },
      },
      legend: { data: ['Ad Spend', 'Order Revenue'], bottom: 0 },
      grid: { top: 16, right: 16, bottom: 40, left: 70, containLabel: false },
      xAxis: {
        type: 'category' as const,
        data: categories,
        axisLabel: { rotate: categories.length > 6 ? 30 : 0 },
      },
      yAxis: {
        type: 'value' as const,
        axisLabel: { formatter: (v: number) => formatCurrencyCompact(v) },
      },
      series: [
        {
          name: 'Ad Spend',
          type: 'bar',
          data: adSpend,
          itemStyle: { color: CHART_COLORS[7], borderRadius: [4, 4, 0, 0] },
          barGap: '10%',
        },
        {
          name: 'Order Revenue',
          type: 'bar',
          data: orderRevenue,
          itemStyle: { color: CHART_COLORS[0], borderRadius: [4, 4, 0, 0] },
        },
      ],
    };
  }, [data]);

  if (!data.length || !option) return null;

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>Category Marketing ROI</h3>
      <ReactECharts option={option} style={{ height: 320 }} />
    </div>
  );
}
