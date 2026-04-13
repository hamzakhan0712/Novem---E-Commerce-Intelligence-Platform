import { Table, Tag, Empty } from 'antd';
import { WarningOutlined } from '@ant-design/icons';

import type { RevenueAtRisk, AtRiskCustomer } from '@/types/dashboard';
import { formatCurrency } from '@/utils/formatCurrency';

import styles from './RevenueAtRiskCard.module.css';

interface Props {
  data: RevenueAtRisk | null;
}

const columns = [
  {
    title: 'Customer',
    dataIndex: 'customer_id',
    key: 'customer_id',
    ellipsis: true,
    render: (v: string) => v.slice(0, 12) + '…',
  },
  {
    title: 'Est. Loss',
    dataIndex: 'estimated_loss',
    key: 'estimated_loss',
    sorter: (a: AtRiskCustomer, b: AtRiskCustomer) => b.estimated_loss - a.estimated_loss,
    render: (v: number) => <span className={styles.lossValue}>{formatCurrency(v)}</span>,
  },
  {
    title: 'Days Overdue',
    dataIndex: 'days_overdue',
    key: 'days_overdue',
    sorter: (a: AtRiskCustomer, b: AtRiskCustomer) => b.days_overdue - a.days_overdue,
    render: (v: number) => <Tag color={v > 30 ? 'red' : 'orange'}>{v}d</Tag>,
  },
  {
    title: 'Past Avg. Order',
    dataIndex: 'historical_aov',
    key: 'historical_aov',
    render: (v: number) => formatCurrency(v),
  },
];

export default function RevenueAtRiskCard({ data }: Props) {
  if (!data || data.customers_at_risk === 0) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <WarningOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>Revenue At Risk</span>
        </div>
        <Empty description="No at-risk revenue detected" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <WarningOutlined className={styles.headerIcon} />
        <span className={styles.headerTitle}>Revenue At Risk</span>
      </div>

      <div className={styles.summaryRow}>
        <div className={styles.riskPrimary}>
          <span className={styles.riskAmount}>{formatCurrency(data.total_at_risk)}</span>
          <span className={styles.riskDesc}>
            at risk in next {data.lookahead_days} days
          </span>
        </div>
        <div className={styles.statsRow}>
          <div className={styles.stat}>
            <span className={styles.statValue}>{data.customers_at_risk}</span>
            <span className={styles.statLabel}>At Risk</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statValue}>{data.total_customers_analyzed}</span>
            <span className={styles.statLabel}>Analyzed</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statValue}>{Math.round(data.avg_days_overdue)}d</span>
            <span className={styles.statLabel}>Avg Overdue</span>
          </div>
        </div>
      </div>

      <div className={styles.tableWrap}>
        <Table
          dataSource={data.top_at_risk_customers.slice(0, 5)}
          columns={columns}
          rowKey="customer_id"
          size="small"
          pagination={false}
        />
      </div>
    </div>
  );
}
