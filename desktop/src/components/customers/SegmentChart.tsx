import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

import { useAppStore } from '@/stores/appStore';
import { formatCurrency } from '@/utils/formatCurrency';

import type { CustomerSegment } from '@/types/customers';

import styles from './SegmentChart.module.css';

interface Props {
  segments: CustomerSegment[];
}

const SEGMENT_COLORS: Record<string, string> = {
  Champions: '#52c41a',
  Loyal: '#1890ff',
  Promising: '#722ed1',
  'At Risk': '#faad14',
  'Needs Attention': '#fa8c16',
  Lost: '#ff4d4f',
  VIP: '#52c41a',
  Regular: '#1890ff',
  'Low-spend': '#faad14',
};

export default function SegmentChart({ segments }: Props) {
  const themeMode = useAppStore((s) => s.themeMode);
  const isDark = themeMode === 'dark';
  const textColor = isDark ? '#e0e0e0' : '#333';

  if (segments.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Customer Segments</div>
        <div className={styles.emptyWrap}>
          <Empty description="No segment data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: { name: string; value: number; percent: number; dataIndex: number }) => {
        const seg = segments[params.dataIndex];
        return `<b>${params.name}</b><br/>
          Customers: ${params.value} (${params.percent}%)<br/>
          Total Spend: ${formatCurrency(seg?.total_spend ?? 0)}<br/>
          Avg Spend: ${formatCurrency(seg?.avg_spend ?? 0)}`;
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: textColor, fontSize: 12 },
      itemGap: 16,
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 11,
          color: textColor,
        },
        labelLine: { length: 12, length2: 8 },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
          scaleSize: 6,
        },
        data: segments.map((s) => ({
          name: s.segment,
          value: s.count,
          itemStyle: { color: SEGMENT_COLORS[s.segment] || '#999' },
        })),
      },
    ],
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div className={styles.title}>Customer Segments</div>
        <span className={styles.subtitle}>{segments.length} segments</span>
      </div>
      <ReactECharts option={option} className={styles.chart} />
    </div>
  );
}
