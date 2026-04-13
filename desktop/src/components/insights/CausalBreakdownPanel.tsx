import { Tag, Empty, Tooltip } from 'antd';
import { FundOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { CausalBreakdown } from '@/types/insights';

import styles from './CausalBreakdownPanel.module.css';

interface Props {
  breakdown: CausalBreakdown | null;
}

function fmtDollars(n: number): string {
  const sign = n >= 0 ? '+' : '-';
  return sign + formatCurrency(Math.abs(n));
}

export default function CausalBreakdownPanel({ breakdown }: Props) {
  if (!breakdown || breakdown.drivers.length === 0) {
    return (
      <div className={styles.wrapper}>
        <h3 className={styles.title}>
          <FundOutlined style={{ marginRight: 8 }} />
          Revenue Drivers
        </h3>
        <div className={styles.emptyWrap}>
          <Empty description="No driver analysis available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h3 className={styles.title}>
          <FundOutlined style={{ marginRight: 8 }} />
          Why Did Revenue Change?
        </h3>
        <Tag color={breakdown.change_amount >= 0 ? 'green' : 'red'}>
          {fmtDollars(breakdown.change_amount)} ({breakdown.change_pct >= 0 ? '+' : ''}{breakdown.change_pct.toFixed(1)}%)
        </Tag>
      </div>

      <p className={styles.narrative}>{breakdown.narrative}</p>

      <div className={styles.drivers}>
        {breakdown.drivers.map((d, i) => {
          const pct = breakdown.previous_value > 0
            ? Math.abs(d.impact / breakdown.previous_value * 100)
            : 0;
          return (
            <div key={i} className={styles.driverRow}>
              <div className={styles.driverLeft}>
                <span className={`${styles.dirIcon} ${d.direction === 'up' ? styles.up : styles.down}`}>
                  {d.direction === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                </span>
                <span className={styles.driverName}>{d.driver}</span>
              </div>
              <Tooltip title={d.detail}>
                <div className={styles.driverRight}>
                  <div className={styles.barWrap}>
                    <div
                      className={`${styles.bar} ${d.impact >= 0 ? styles.barPositive : styles.barNegative}`}
                      style={{ width: `${Math.min(pct * 2, 100)}%` }}
                    />
                  </div>
                  <span className={`${styles.impactValue} ${d.impact >= 0 ? styles.positive : styles.negative}`}>
                    {fmtDollars(d.impact)}
                  </span>
                </div>
              </Tooltip>
            </div>
          );
        })}
      </div>
    </div>
  );
}
