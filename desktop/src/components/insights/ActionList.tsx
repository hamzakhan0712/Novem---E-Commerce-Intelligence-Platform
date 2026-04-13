import { Tag, Empty } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { RecommendedAction } from '@/types/insights';

import styles from './ActionList.module.css';

interface Props {
  actions: RecommendedAction[];
}

function priorityColor(p: string): string {
  if (p === 'high') return 'red';
  if (p === 'medium') return 'orange';
  return 'green';
}

function impactLabel(action: RecommendedAction): string {
  const base = `${action.impact} impact · ${action.effort} effort`;
  if (action.impact_dollars && action.impact_dollars > 0) {
    return `${formatCurrency(action.impact_dollars)} potential · ${base}`;
  }
  return base;
}

export default function ActionList({ actions }: Props) {
  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>
        <ThunderboltOutlined style={{ marginRight: 8 }} />
        Recommended Actions
      </h3>

      {actions.length === 0 ? (
        <div className={styles.emptyWrap}>
          <Empty description="No recommendations currently" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div className={styles.list}>
          {actions.map((action, i) => (
            <div key={i} className={styles.item}>
              <div className={styles.rankBadge}>
                <span className={styles.rankNumber}>{action.rank}</span>
              </div>
              <div className={styles.content}>
                <div className={styles.headerRow}>
                  <span className={styles.actionTitle}>{action.title}</span>
                  <Tag color={priorityColor(action.priority)}>{action.priority}</Tag>
                </div>
                <p className={styles.description}>{action.description}</p>
                <span className={styles.meta}>{impactLabel(action)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
