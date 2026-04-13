import { Table, Tag, Empty } from 'antd';
import { WarningOutlined, ClockCircleOutlined, CheckCircleOutlined, SafetyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';

import { CHART_COLORS } from '@/constants/theme';
import type { StockForecastData, StockForecastProduct } from '@/types/products';

import styles from './StockForecastPanel.module.css';

interface StockForecastPanelProps {
  data: StockForecastData | null;
}

const URGENCY_CONFIG: Record<string, { color: string; label: string; chartColor: string; icon: React.ReactNode }> = {
  stockout_imminent: { color: 'red', label: 'Stockout Imminent', chartColor: CHART_COLORS[7], icon: <WarningOutlined /> },
  low_stock: { color: 'orange', label: 'Low Stock', chartColor: CHART_COLORS[4], icon: <ClockCircleOutlined /> },
  adequate: { color: 'blue', label: 'Adequate', chartColor: CHART_COLORS[1], icon: <CheckCircleOutlined /> },
  well_stocked: { color: 'green', label: 'Well Stocked', chartColor: CHART_COLORS[0], icon: <SafetyOutlined /> },
};

function buildDonutOption(summary: StockForecastData['summary']) {
  const data = [
    { name: 'Stockout Imminent', value: summary.stockout_imminent, itemStyle: { color: CHART_COLORS[7] } },
    { name: 'Low Stock', value: summary.low_stock, itemStyle: { color: CHART_COLORS[4] } },
    { name: 'Adequate', value: summary.adequate, itemStyle: { color: CHART_COLORS[1] } },
    { name: 'Well Stocked', value: summary.well_stocked, itemStyle: { color: CHART_COLORS[0] } },
  ].filter((d) => d.value > 0);

  const total = data.reduce((s, d) => s + d.value, 0);

  return {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['50%', '72%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: true,
      label: {
        show: true,
        position: 'center' as const,
        formatter: `{a|${total}}\n{b|products}`,
        rich: {
          a: { fontSize: 22, fontWeight: 'bold' as const, lineHeight: 28 },
          b: { fontSize: 11, color: '#999', lineHeight: 16 },
        },
      },
      data,
    }],
  };
}

export default function StockForecastPanel({ data }: StockForecastPanelProps) {
  if (!data || !data.products.length) {
    return <Empty description="No stock forecast data available." />;
  }

  const { summary, products } = data;

  const columns: ColumnsType<StockForecastProduct> = [
    { title: 'Product', dataIndex: 'product_name', ellipsis: true },
    { title: 'Category', dataIndex: 'category', width: 130 },
    {
      title: 'Urgency',
      dataIndex: 'urgency',
      width: 160,
      render: (u: string) => {
        const cfg = URGENCY_CONFIG[u] || { color: 'default', label: u, icon: null };
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>;
      },
      filters: Object.entries(URGENCY_CONFIG).map(([value, cfg]) => ({ text: cfg.label, value })),
      onFilter: (value, record) => record.urgency === value,
    },
    {
      title: 'Current Stock',
      dataIndex: 'current_stock',
      width: 110,
      align: 'right',
      render: (v: number) => v.toLocaleString('en-IN'),
      sorter: (a, b) => a.current_stock - b.current_stock,
    },
    {
      title: 'Daily Demand',
      dataIndex: 'avg_daily_demand',
      width: 110,
      align: 'right',
      render: (v: number) => v.toFixed(1),
      sorter: (a, b) => a.avg_daily_demand - b.avg_daily_demand,
    },
    {
      title: 'Days Left',
      dataIndex: 'days_until_stockout',
      width: 100,
      align: 'right',
      render: (v: number) => v >= 999 ? '∞' : `${v.toFixed(0)}d`,
      sorter: (a, b) => a.days_until_stockout - b.days_until_stockout,
      defaultSortOrder: 'ascend',
    },
    {
      title: 'Est. Stockout',
      dataIndex: 'predicted_stockout_date',
      width: 120,
      render: (v: string | null) => v || '—',
    },
  ];

  return (
    <div className={styles.panel}>
      <div className={styles.topRow}>
        <div className={styles.summaryCards}>
          {(['stockout_imminent', 'low_stock', 'adequate', 'well_stocked'] as const).map((key) => {
            const cfg = URGENCY_CONFIG[key];
            const count = summary[key];
            return (
              <div key={key} className={styles.statCard}>
                <span className={styles.statIcon} style={{ color: cfg.chartColor }}>{cfg.icon}</span>
                <span className={styles.statValue}>{count}</span>
                <span className={styles.statLabel}>{cfg.label}</span>
              </div>
            );
          })}
        </div>
        <div className={styles.donutWrap}>
          <ReactECharts option={buildDonutOption(summary)} style={{ height: 220 }} />
        </div>
      </div>
      <Table
        rowKey="product_id"
        columns={columns}
        dataSource={products}
        size="small"
        pagination={{ pageSize: 12, showSizeChanger: false }}
        scroll={{ x: 800 }}
      />
    </div>
  );
}
