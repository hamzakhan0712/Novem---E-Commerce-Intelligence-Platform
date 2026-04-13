import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

import styles from './KpiCard.module.css';

interface KpiCardProps {
  label: string;
  value: string;
  change: number | null;
  previousValue?: string;
  tooltip?: string;
}

export default function KpiCard({ label, value, change, previousValue, tooltip }: KpiCardProps) {
  const isUp = change !== null && change > 0;
  const isDown = change !== null && change < 0;

  return (
    <div className={styles.card}>
      <span className={styles.label}>
        {label}
        {tooltip && (
          <Tooltip title={tooltip}>
            <InfoCircleOutlined className={styles.infoIcon} />
          </Tooltip>
        )}
      </span>
      <div className={styles.valueRow}>
        <span className={styles.value}>{value}</span>
        {change !== null && (
          <span
            className={`${styles.change} ${isUp ? styles.changeUp : isDown ? styles.changeDown : styles.changeNeutral}`}
          >
            {isUp ? <ArrowUpOutlined /> : isDown ? <ArrowDownOutlined /> : <MinusOutlined />}
            {Math.abs(change)}%
          </span>
        )}
      </div>
      {previousValue && (
        <span className={styles.prev}>vs. {previousValue} previous period</span>
      )}
    </div>
  );
}
