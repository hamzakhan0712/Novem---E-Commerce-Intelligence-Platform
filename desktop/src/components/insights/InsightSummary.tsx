import { BulbOutlined, WarningOutlined, ThunderboltOutlined, AlertOutlined } from '@ant-design/icons';

import type { InsightSummary as InsightSummaryType } from '@/types/insights';

import styles from './InsightSummary.module.css';

interface Props {
  summary: InsightSummaryType;
}

export default function InsightSummary({ summary }: Props) {
  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <div className={`${styles.iconWrap} ${styles.iconInsights}`}>
          <BulbOutlined />
        </div>
        <div className={styles.info}>
          <span className={styles.value}>{summary.total_insights}</span>
          <span className={styles.label}>Insights</span>
        </div>
      </div>

      <div className={styles.card}>
        <div className={`${styles.iconWrap} ${styles.iconCritical}`}>
          <AlertOutlined />
        </div>
        <div className={styles.info}>
          <span className={styles.value}>{summary.critical_count}</span>
          <span className={styles.label}>Critical</span>
        </div>
      </div>

      <div className={styles.card}>
        <div className={`${styles.iconWrap} ${styles.iconAnomalies}`}>
          <WarningOutlined />
        </div>
        <div className={styles.info}>
          <span className={styles.value}>{summary.anomaly_count}</span>
          <span className={styles.label}>Anomalies</span>
        </div>
      </div>

      <div className={styles.card}>
        <div className={`${styles.iconWrap} ${styles.iconActions}`}>
          <ThunderboltOutlined />
        </div>
        <div className={styles.info}>
          <span className={styles.value}>{summary.action_count}</span>
          <span className={styles.label}>Actions</span>
        </div>
      </div>
    </div>
  );
}
