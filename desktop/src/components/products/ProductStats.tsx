import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

import { formatCurrency } from '@/utils/formatCurrency';

import styles from './ProductStats.module.css';

import type { ProductSummary } from '@/types/products';

interface Props {
  summary: ProductSummary;
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

export default function ProductStats({ summary }: Props) {
  const { current, previous, changes } = summary;

  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <span className={styles.label}>
          Products Sold
          <Tooltip title="Different products with at least one completed order in this period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{fmt(current.products_sold)}</span>
          <ChangeIndicator value={changes.products_sold} />
        </div>
        <span className={styles.sub}>across {fmt(current.categories)} categories</span>
        <span className={styles.prev}>vs. {fmt(previous.products_sold)} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Units Sold
          <Tooltip title="Total quantity of items sold across all completed orders">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{fmt(current.total_units)}</span>
          <ChangeIndicator value={changes.total_units} />
        </div>
        <span className={styles.prev}>vs. {fmt(previous.total_units)} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Product Revenue
          <Tooltip title="Net revenue (price minus discounts) from completed orders for all products">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatCurrency(current.total_revenue)}</span>
          <ChangeIndicator value={changes.total_revenue} />
        </div>
        <span className={styles.prev}>vs. {formatCurrency(previous.total_revenue)} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Avg. Price
          <Tooltip title="Average net revenue per unit sold (total product revenue / units sold)">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{formatCurrency(current.avg_price)}</span>
          <ChangeIndicator value={changes.avg_price} />
        </div>
        <span className={styles.sub}>per unit sold</span>
        <span className={styles.prev}>vs. {formatCurrency(previous.avg_price)} previous period</span>
      </div>
    </div>
  );
}
