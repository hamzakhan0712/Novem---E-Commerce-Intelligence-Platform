import { Table, Tag, Empty, Progress } from 'antd';
import {
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InboxOutlined,
} from '@ant-design/icons';

import type { InventoryAnalysis, InventoryProduct } from '@/types/products';

import styles from './InventoryPanel.module.css';

interface Props {
  data: InventoryAnalysis | null;
}

function statusTag(status: string) {
  switch (status) {
    case 'critical': return <Tag color="red" icon={<WarningOutlined />}>Critical</Tag>;
    case 'reorder_now': return <Tag color="orange" icon={<ExclamationCircleOutlined />}>Reorder Now</Tag>;
    case 'healthy': return <Tag color="green" icon={<CheckCircleOutlined />}>Healthy</Tag>;
    case 'overstocked': return <Tag color="blue" icon={<InboxOutlined />}>Overstocked</Tag>;
    case 'no_data': return <Tag color="default">No Stock Data</Tag>;
    default: return <Tag>{status}</Tag>;
  }
}

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
    width: 120,
    ellipsis: true,
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    render: (v: string) => statusTag(v),
    width: 140,
  },
  {
    title: 'Current Stock',
    dataIndex: 'current_stock',
    key: 'current_stock',
    width: 110,
  },
  {
    title: 'Days of Stock',
    dataIndex: 'days_of_stock',
    key: 'days_of_stock',
    render: (v: number) => {
      const pct = Math.min(v / 90 * 100, 100);
      const color = v < 7 ? '#ff4d4f' : v < 30 ? '#faad14' : '#52c41a';
      return <Progress percent={pct} size="small" strokeColor={color} format={() => `${v.toFixed(0)}d`} />;
    },
    sorter: (a: InventoryProduct, b: InventoryProduct) => a.days_of_stock - b.days_of_stock,
    width: 140,
  },
  {
    title: 'Reorder At',
    dataIndex: 'reorder_point',
    key: 'reorder_point',
    width: 110,
  },
  {
    title: 'Buffer Stock',
    dataIndex: 'safety_stock',
    key: 'safety_stock',
    width: 100,
  },
  {
    title: 'Order Qty',
    dataIndex: 'economic_order_qty',
    key: 'economic_order_qty',
    width: 80,
  },
  {
    title: 'Avg. Daily Demand',
    dataIndex: 'avg_daily_demand',
    key: 'avg_daily_demand',
    render: (v: number) => v.toFixed(1),
    width: 130,
  },
  {
    title: 'Delivery Time',
    dataIndex: 'lead_time_days',
    key: 'lead_time_days',
    render: (v: number) => `${v}d`,
    width: 90,
  },
];

export default function InventoryPanel({ data }: Props) {
  if (!data || !data.products.length) {
    return <Empty description={data?.message || 'No inventory data available.'} />;
  }

  const { summary, products } = data;

  return (
    <div className={styles.panel}>
      <div className={styles.summaryRow}>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Total Products</span>
          <span className={styles.statValue}>{summary.total_products}</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Needs Reorder</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#ff4d4f' }}><WarningOutlined /></span>
            <span className={styles.statValue}>{summary.needs_reorder}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Healthy</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#52c41a' }}><CheckCircleOutlined /></span>
            <span className={styles.statValue}>{summary.healthy}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Overstocked</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#1677ff' }}><InboxOutlined /></span>
            <span className={styles.statValue}>{summary.overstocked}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>No Data</span>
          <span className={styles.statValue}>{summary.no_stock_data}</span>
        </div>
      </div>

      <Table
        dataSource={products}
        columns={columns}
        rowKey="product_id"
        size="small"
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 1200 }}
      />
    </div>
  );
}
