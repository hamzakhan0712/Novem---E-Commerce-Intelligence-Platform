import { Table, Tag, Progress, Empty } from 'antd';
import { WarningOutlined, CheckCircleOutlined, UserOutlined } from '@ant-design/icons';

import type { ChurnPrediction, ChurnCustomer } from '@/types/customers';

import { formatCurrency } from '@/utils/formatCurrency';

import styles from './ChurnRiskPanel.module.css';

interface Props {
  data: ChurnPrediction | null;
}

function riskTag(risk: string) {
  switch (risk) {
    case 'high': return <Tag color="red">High Risk</Tag>;
    case 'medium': return <Tag color="orange">Medium</Tag>;
    case 'low': return <Tag color="green">Low</Tag>;
    default: return <Tag>{risk}</Tag>;
  }
}

const columns = [
  {
    title: 'Customer',
    dataIndex: 'customer_id',
    key: 'customer_id',
    ellipsis: true,
  },
  {
    title: 'Risk Level',
    dataIndex: 'churn_risk',
    key: 'churn_risk',
    render: (v: string) => riskTag(v),
    width: 110,
  },
  {
    title: 'Active Chance',
    dataIndex: 'p_alive',
    key: 'p_alive',
    render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" strokeColor={v > 0.6 ? '#52c41a' : v > 0.3 ? '#faad14' : '#ff4d4f'} />,
    width: 150,
  },
  {
    title: 'Expected Orders',
    dataIndex: 'predicted_purchases',
    key: 'predicted_purchases',
    render: (v: number) => v.toFixed(1),
    width: 130,
  },
  {
    title: 'Est. Customer Value',
    dataIndex: 'expected_clv',
    key: 'expected_clv',
    render: (v: number) => formatCurrency(v),
    sorter: (a: ChurnCustomer, b: ChurnCustomer) => a.expected_clv - b.expected_clv,
    defaultSortOrder: 'descend' as const,
    width: 120,
  },
  {
    title: 'Last Order',
    dataIndex: 'recency_days',
    key: 'recency_days',
    render: (v: number) => `${v}d ago`,
    width: 90,
  },
  {
    title: 'Orders',
    dataIndex: 'frequency',
    key: 'frequency',
    width: 90,
  },
  {
    title: 'Avg. Order',
    dataIndex: 'avg_order_value',
    key: 'avg_order_value',
    render: (v: number) => formatCurrency(v),
    width: 110,
  },
];

export default function ChurnRiskPanel({ data }: Props) {
  if (!data || !data.customers?.length) {
    return <Empty description="Not enough repeat purchase data yet. Import more orders to see which customers may stop buying." />;
  }

  const { summary, customers, model } = data;

  return (
    <div className={styles.panel}>
      <div className={styles.summaryRow}>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Total Scored</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon}><UserOutlined /></span>
            <span className={styles.statValue}>{summary.total_scored}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>High Risk</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#ff4d4f' }}><WarningOutlined /></span>
            <span className={styles.statValue}>{summary.high_risk}</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Medium Risk</span>
          <span className={styles.statValue}>{summary.medium_risk}</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Low Risk</span>
          <div className={styles.statValueRow}>
            <span className={styles.statIcon} style={{ color: '#52c41a' }}><CheckCircleOutlined /></span>
            <span className={styles.statValue}>{summary.low_risk}</span>
          </div>
        </div>
      </div>

      <div className={styles.modelInfo}>
        Method: <Tag color="blue">{model}</Tag>
        Avg. Active Probability: <strong>{(summary.avg_alive_probability * 100).toFixed(1)}%</strong>
      </div>

      <Table
        dataSource={customers}
        columns={columns}
        rowKey="customer_id"
        size="small"
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 900 }}
      />
    </div>
  );
}
