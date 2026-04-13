import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

import { formatCurrency } from '@/utils/formatCurrency';

import styles from './CustomerStats.module.css';

import type { CustomerSummary } from '@/types/customers';

interface Props {
  summary: CustomerSummary;
}

function fmt(n: number): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function ChangeIndicator({ value }: { value: number }) {
  const isUp = value > 0;
  const isDown = value < 0;
  const cls = isUp ? styles.changeUp : isDown ? styles.changeDown : styles.changeNeutral;

  return (
    <span className={`${styles.change} ${cls}`}>
      {isUp ? <ArrowUpOutlined /> : isDown ? <ArrowDownOutlined /> : <MinusOutlined />}
      {Math.abs(value)}%
    </span>
  );
}

export default function CustomerStats({ summary }: Props) {
  const { current, previous, changes } = summary;

  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <span className={styles.label}>
          Total Customers
          <Tooltip title="Unique customers with at least one completed order in the selected period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{fmt(current.total_customers)}</span>
          <ChangeIndicator value={changes.total_customers} />
        </div>
        <span className={styles.sub}>
          {fmt(current.one_time_customers)} new &middot; {fmt(current.returning_customers)} returning
        </span>
        <span className={styles.prev}>vs. {fmt(previous.total_customers)} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Returning Rate
          <Tooltip title="Percentage of customers who placed more than one completed order">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{current.returning_rate}%</span>
          <ChangeIndicator value={changes.returning_rate} />
        </div>
        <span className={styles.sub}>of customers came back</span>
        <span className={styles.prev}>vs. {previous.returning_rate}% previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Total Spend
          <Tooltip title="Sum of net revenue (price minus discounts) from all completed orders by these customers">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatCurrency(current.total_spend)}</span>
          <ChangeIndicator value={changes.total_spend} />
        </div>
        <span className={styles.prev}>vs. {formatCurrency(previous.total_spend)} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Avg. Customer Value
          <Tooltip title="Total net spend divided by number of unique customers in this period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatCurrency(current.avg_lifetime_value)}</span>
          <ChangeIndicator value={changes.avg_lifetime_value} />
        </div>
        <span className={styles.sub}>per customer this period</span>
        <span className={styles.prev}>vs. {formatCurrency(previous.avg_lifetime_value)} previous period</span>
      </div>
    </div>
  );
}
