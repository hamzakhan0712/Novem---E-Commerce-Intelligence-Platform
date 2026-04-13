import { Table, Tag, Empty } from 'antd';
import { RocketOutlined, DollarOutlined, FallOutlined, StopOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

import type { ProductLifecycle, LifecycleProduct, LifecycleStage } from '@/types/products';
import { formatCurrency } from '@/utils/formatCurrency';

import styles from './LifecyclePanel.module.css';

interface Props {
  data: ProductLifecycle | null;
}

const stageConfig: Record<LifecycleStage, { color: string; icon: React.ReactNode; label: string }> = {
  rising_star: { color: 'green', icon: <RocketOutlined />, label: 'Rising Star' },
  cash_cow: { color: 'blue', icon: <DollarOutlined />, label: 'Cash Cow' },
  fading_out: { color: 'orange', icon: <FallOutlined />, label: 'Fading Out' },
  dead_weight: { color: 'red', icon: <StopOutlined />, label: 'Dead Weight' },
};

const columns = [
  {
    title: 'Product',
    dataIndex: 'product_name',
    key: 'product_name',
    ellipsis: true,
  },
  {
    title: 'Category',
    dataIndex: 'category',
    key: 'category',
  },
  {
    title: 'Stage',
    dataIndex: 'lifecycle_stage',
    key: 'lifecycle_stage',
    filters: [
      { text: 'Rising Star', value: 'rising_star' },
      { text: 'Cash Cow', value: 'cash_cow' },
      { text: 'Fading Out', value: 'fading_out' },
      { text: 'Dead Weight', value: 'dead_weight' },
    ],
    onFilter: (value: unknown, record: LifecycleProduct) => record.lifecycle_stage === value,
    render: (stage: LifecycleStage) => {
      const cfg = stageConfig[stage];
      return <Tag icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>;
    },
  },
  {
    title: 'Revenue',
    dataIndex: 'total_revenue',
    key: 'total_revenue',
    sorter: (a: LifecycleProduct, b: LifecycleProduct) => b.total_revenue - a.total_revenue,
    render: (v: number) => formatCurrency(v),
  },
  {
    title: 'Trend',
    dataIndex: 'revenue_trend',
    key: 'revenue_trend',
    sorter: (a: LifecycleProduct, b: LifecycleProduct) => b.revenue_trend - a.revenue_trend,
    render: (v: number) => (
      <span style={{ color: v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : '#8c8c8c' }}>
        {v > 0 ? '+' : ''}{(v * 100).toFixed(0)}%
      </span>
    ),
  },
  {
    title: 'Recommendation',
    dataIndex: 'recommendation',
    key: 'recommendation',
    ellipsis: true,
  },
];

function buildScatterOption(products: LifecycleProduct[]) {
  const colorMap: Record<LifecycleStage, string> = {
    rising_star: '#52c41a',
    cash_cow: '#1890ff',
    fading_out: '#faad14',
    dead_weight: '#ff4d4f',
  };

  const seriesData = products.map((p) => ({
    value: [p.revenue_trend * 100, p.total_revenue, p.order_count],
    name: p.product_name,
    itemStyle: { color: colorMap[p.lifecycle_stage] },
  }));

  return {
    tooltip: {
      formatter: (params: { name: string; value: number[] }) => {
        return `${params.name}<br/>Trend: ${params.value[0].toFixed(0)}%<br/>Revenue: ${formatCurrency(params.value[1])}<br/>Orders: ${params.value[2]}`;
      },
    },
    xAxis: { name: 'Revenue Trend %', type: 'value' as const },
    yAxis: { name: 'Total Revenue', type: 'value' as const },
    series: [
      {
        type: 'scatter',
        data: seriesData,
        symbolSize: (val: number[]) => Math.max(8, Math.min(40, val[2] / 2)),
      },
    ],
  };
}

export default function LifecyclePanel({ data }: Props) {
  if (!data || !data.products.length) {
    return <Empty description="No product lifecycle data available" />;
  }

  const { summary } = data;

  return (
    <div className={styles.panel}>
      <div className={styles.summaryRow}>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Rising Stars</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#52c41a' }}><RocketOutlined /></span>
            <span className={styles.statValue}>{summary.rising_star}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Cash Cows</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#1890ff' }}><DollarOutlined /></span>
            <span className={styles.statValue}>{summary.cash_cow}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Fading Out</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#faad14' }}><FallOutlined /></span>
            <span className={styles.statValue}>{summary.fading_out}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Dead Weight</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#ff4d4f' }}><StopOutlined /></span>
            <span className={styles.statValue}>{summary.dead_weight}</span>
          </div>
        </div>
      </div>

      <div className={styles.chartWrap}>
        <h3 className={styles.chartTitle}>Product Performance Map</h3>
        <ReactECharts option={buildScatterOption(data.products)} style={{ height: 300 }} />
      </div>

      <Table
        dataSource={data.products}
        columns={columns}
        rowKey="product_id"
        size="small"
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
}
