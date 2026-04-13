import { Tag, Empty, Tooltip } from 'antd';
import { WarningOutlined, ClockCircleOutlined } from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { Anomaly } from '@/types/insights';

import styles from './AnomalyList.module.css';

interface Props {
  anomalies: Anomaly[];
}

function getSeverityTag(severity: string) {
  const colorMap: Record<string, string> = { high: 'red', medium: 'orange', low: 'gold' };
  return <Tag color={colorMap[severity] || 'default'}>{severity}</Tag>;
}

function formatDetectionTime(hours: number | null | undefined): string | null {
  if (hours == null) return null;
  if (hours < 1) return '<1h';
  if (hours < 24) return `${Math.round(hours)}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

export default function AnomalyList({ anomalies }: Props) {
  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>
        <WarningOutlined style={{ marginRight: 8 }} />
        Unusual Activity
      </h3>

      {anomalies.length === 0 ? (
        <div className={styles.emptyWrap}>
          <Empty description="No unusual activity detected" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div className={styles.list}>
          {anomalies.map((a, i) => (
            <div key={i} className={styles.item}>
              <div className={styles.left}>
                <span className={styles.date}>{a.date}</span>
                <span className={`${styles.direction} ${a.direction === 'spike' ? styles.spike : styles.drop}`}>
                  {a.direction === 'spike' ? '▲' : '▼'} {a.direction}
                </span>
              </div>
              <div className={styles.detail}>
                <span className={styles.values}>
                  {formatCurrency(a.value)} vs expected {formatCurrency(a.expected)}
                </span>
                <span className={styles.zscore}>{a.z_score}x above normal</span>
              </div>
              <div className={styles.right}>
                {a.time_to_detection_hours != null && (
                  <Tooltip title={`Detected ${formatDetectionTime(a.time_to_detection_hours)} after occurrence`}>
                    <span className={styles.detection}>
                      <ClockCircleOutlined /> {formatDetectionTime(a.time_to_detection_hours)}
                    </span>
                  </Tooltip>
                )}
                {getSeverityTag(a.severity)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
