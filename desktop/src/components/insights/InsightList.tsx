import { useState, useMemo } from 'react';

import { Tag, Empty, Segmented } from 'antd';
import { BulbOutlined } from '@ant-design/icons';

import type { Insight } from '@/types/insights';

import styles from './InsightList.module.css';

interface Props {
  insights: Insight[];
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'positive': return 'green';
    case 'negative': return 'red';
    case 'warning': return 'orange';
    default: return 'blue';
  }
}

function getPriorityClass(priority: number): string {
  if (priority <= 10) return styles.iconCritical;
  if (priority <= 20) return styles.iconWarning;
  return styles.iconInfo;
}

export default function InsightList({ insights }: Props) {
  const [filter, setFilter] = useState<string>('all');

  const categories = useMemo(() => {
    const cats = new Set(insights.map((i) => i.category));
    return ['all', ...Array.from(cats).sort()];
  }, [insights]);

  const filtered = useMemo(() => {
    if (filter === 'all') return insights;
    return insights.filter((i) => i.category === filter);
  }, [insights, filter]);

  const filterOptions = useMemo(
    () => categories.map((c) => ({ label: c === 'all' ? 'All' : c.charAt(0).toUpperCase() + c.slice(1), value: c })),
    [categories],
  );

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h3 className={styles.title}>
          <BulbOutlined style={{ marginRight: 8 }} />
          Key Insights
        </h3>
        {categories.length > 2 && (
          <Segmented options={filterOptions} value={filter} onChange={(v) => setFilter(v as string)} size="small" />
        )}
      </div>

      {filtered.length === 0 ? (
        <Empty description="No insights for this filter" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className={styles.list}>
          {filtered.map((insight, i) => (
            <div key={i} className={styles.item}>
              <div className={`${styles.icon} ${getPriorityClass(insight.priority)}`}>
                <BulbOutlined />
              </div>
              <div className={styles.content}>
                <div className={styles.titleRow}>
                  <span className={styles.itemTitle}>{insight.title}</span>
                  <Tag color={getSeverityColor(insight.severity)}>{insight.severity}</Tag>
                </div>
                <p className={styles.message}>{insight.message}</p>
                {insight.suggestion && (
                  <p className={styles.suggestion}>{insight.suggestion}</p>
                )}
                {insight.confidence !== undefined && (
                  <span className={styles.confidence}>{Math.round(insight.confidence * 100)}% confidence</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
