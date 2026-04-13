import { Tag, Empty, Progress } from 'antd';
import { DollarOutlined } from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { MissedRevenueSummary } from '@/types/insights';

import styles from './MissedRevenuePanel.module.css';

interface Props {
  data: MissedRevenueSummary | null;
}

function fmtDollars(n: number): string {
  return formatCurrency(n);
}

function typeColor(type: string): string {
  if (type === 'refund') return 'red';
  if (type === 'churn') return 'orange';
  return 'gold';
}

function typeLabel(type: string): string {
  if (type === 'refund') return 'Refund';
  if (type === 'churn') return 'Lost Customers';
  return 'Stockout';
}

export default function MissedRevenuePanel({ data }: Props) {
  if (!data || data.total_missed_revenue === 0) {
    return (
      <div className={styles.wrapper}>
        <h3 className={styles.title}>
          <DollarOutlined style={{ marginRight: 8 }} />
          Missed Revenue
        </h3>
        <div className={styles.emptyWrap}>
          <Empty description="No missed revenue detected" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const { refunds, churned_customers, stockout_signals } = data.breakdown;
  const total = data.total_missed_revenue;

  const segments = [
    { key: 'Refunds', value: refunds.total, count: refunds.count, color: '#ff4d4f' },
    { key: 'Lost Customers', value: churned_customers.total, count: churned_customers.count, color: '#fa8c16' },
    { key: 'Stockouts', value: stockout_signals.total, count: stockout_signals.count, color: '#faad14' },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h3 className={styles.title}>
          <DollarOutlined style={{ marginRight: 8 }} />
          Missed Revenue
        </h3>
        <span className={styles.totalBadge}>{fmtDollars(total)} potential</span>
      </div>

      <div className={styles.segments}>
        {segments.map((s) => {
          const pct = total > 0 ? (s.value / total) * 100 : 0;
          return (
            <div key={s.key} className={styles.segment}>
              <div className={styles.segmentHeader}>
                <span className={styles.segmentLabel}>{s.key}</span>
                <span className={styles.segmentValue}>{fmtDollars(s.value)}</span>
              </div>
              <Progress percent={Math.round(pct)} size="small" strokeColor={s.color} showInfo={false} />
              <span className={styles.segmentCount}>{s.count} item{s.count !== 1 ? 's' : ''}</span>
            </div>
          );
        })}
      </div>

      {data.opportunities.length > 0 && (
        <div className={styles.opList}>
          <h4 className={styles.opTitle}>Top Opportunities</h4>
          {data.opportunities.slice(0, 5).map((op, i) => (
            <div key={i} className={styles.opItem}>
              <Tag color={typeColor(op.type)}>{typeLabel(op.type)}</Tag>
              <span className={styles.opDesc}>{op.description}</span>
              <span className={styles.opAmount}>{fmtDollars(op.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
