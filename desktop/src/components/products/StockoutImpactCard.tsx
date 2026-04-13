import { Table, Empty, Tag } from 'antd';
import { DollarOutlined, CalendarOutlined, ShoppingOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { CHART_COLORS } from '@/constants/theme';
import { formatCurrency } from '@/utils/formatCurrency';
import type { StockoutImpactData, StockoutEvent } from '@/types/products';

import styles from './StockoutImpactCard.module.css';

interface StockoutImpactCardProps {
  data: StockoutImpactData | null;
}

export default function StockoutImpactCard({ data }: StockoutImpactCardProps) {
  if (!data || !data.events.length) {
    return (
      <Empty description={data?.message || "No stockout events detected — great job keeping products in stock!"} />
    );
  }

  const columns: ColumnsType<StockoutEvent> = [
    { title: 'Product', dataIndex: 'product_name', ellipsis: true },
    {
      title: 'Category',
      dataIndex: 'category',
      width: 130,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: 'Start', dataIndex: 'stockout_start', width: 110 },
    { title: 'End', dataIndex: 'stockout_end', width: 110 },
    {
      title: 'Days',
      dataIndex: 'stockout_days',
      width: 70,
      align: 'right',
      sorter: (a, b) => a.stockout_days - b.stockout_days,
      render: (v: number) => <span style={{ color: v >= 14 ? CHART_COLORS[7] : v >= 7 ? CHART_COLORS[4] : 'inherit' }}>{v}</span>,
    },
    {
      title: 'Est. Revenue Lost',
      dataIndex: 'estimated_missed_revenue',
      width: 140,
      align: 'right',
      render: (v: number) => <span style={{ color: CHART_COLORS[7] }}>{formatCurrency(v)}</span>,
      sorter: (a, b) => a.estimated_missed_revenue - b.estimated_missed_revenue,
      defaultSortOrder: 'descend',
    },
  ];

  return (
    <div className={styles.panel}>
      <div className={styles.summaryCards}>
        <div className={styles.statCard}>
          <span className={styles.statIcon} style={{ color: CHART_COLORS[7] }}><DollarOutlined /></span>
          <span className={styles.statValue}>{formatCurrency(data.total_estimated_loss)}</span>
          <span className={styles.statLabel}>Est. Revenue Lost</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statIcon} style={{ color: CHART_COLORS[4] }}><CalendarOutlined /></span>
          <span className={styles.statValue}>{data.total_stockout_days}</span>
          <span className={styles.statLabel}>Total Stockout Days</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statIcon} style={{ color: CHART_COLORS[2] }}><ShoppingOutlined /></span>
          <span className={styles.statValue}>{data.products_affected}</span>
          <span className={styles.statLabel}>Products Affected</span>
        </div>
      </div>
      <div className={styles.tableCard}>
        <h3 className={styles.tableTitle}>Stockout Events</h3>
        <Table
          rowKey={(r) => `${r.product_id}-${r.stockout_start}`}
          columns={columns}
          dataSource={data.events}
          size="small"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 700 }}
        />
      </div>
    </div>
  );
}
