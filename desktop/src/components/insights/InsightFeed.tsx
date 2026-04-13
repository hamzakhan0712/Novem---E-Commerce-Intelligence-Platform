import { Tag, Empty } from 'antd';
import {
  BulbOutlined, WarningOutlined, ThunderboltOutlined,
  FundOutlined, DollarOutlined,
} from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { FeedItem } from '@/types/insights';

import styles from './InsightFeed.module.css';

interface Props {
  feed: FeedItem[];
}

const ICON_MAP: Record<string, React.ReactNode> = {
  insight: <BulbOutlined />,
  anomaly: <WarningOutlined />,
  action: <ThunderboltOutlined />,
  causal: <FundOutlined />,
  missed_revenue: <DollarOutlined />,
};

function severityColor(sev: string): string {
  if (sev === 'positive') return 'green';
  if (sev === 'negative') return 'red';
  if (sev === 'warning') return 'orange';
  return 'blue';
}

function feedTypeLabel(t: string): string {
  if (t === 'missed_revenue') return 'Revenue Leak';
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export default function InsightFeed({ feed }: Props) {
  if (feed.length === 0) {
    return (
      <div className={styles.wrapper}>
        <h3 className={styles.title}>Intelligence Feed</h3>
        <div className={styles.emptyWrap}>
          <Empty description="No feed items yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>Intelligence Feed</h3>
      <div className={styles.feed}>
        {feed.map((item) => (
          <div key={item.id} className={styles.item}>
            <div className={`${styles.icon} ${styles[`icon_${item.severity}`]}`}>
              {ICON_MAP[item.feed_type] || <BulbOutlined />}
            </div>
            <div className={styles.content}>
              <div className={styles.itemHeader}>
                <span className={styles.itemTitle}>{item.title}</span>
                <div className={styles.tags}>
                  <Tag color={severityColor(item.severity)} style={{ margin: 0 }}>{item.severity}</Tag>
                  <Tag style={{ margin: 0 }}>{feedTypeLabel(item.feed_type)}</Tag>
                </div>
              </div>
              <p className={styles.message}>{item.message}</p>
              {item.suggestion && <p className={styles.suggestion}>{item.suggestion}</p>}
              {item.metadata?.impact_dollars != null && (
                <span className={styles.impactBadge}>
                  Potential impact: {formatCurrency(Number(item.metadata.impact_dollars))}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
