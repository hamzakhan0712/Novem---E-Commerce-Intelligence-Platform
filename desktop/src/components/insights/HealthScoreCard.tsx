import { Progress } from 'antd';
import { HeartOutlined } from '@ant-design/icons';

import type { BusinessHealthScore } from '@/types/insights';

import styles from './HealthScoreCard.module.css';

interface Props {
  score: BusinessHealthScore | null;
}

function scoreColor(score: number): string {
  if (score >= 80) return '#52c41a';
  if (score >= 65) return '#1890ff';
  if (score >= 45) return '#faad14';
  if (score >= 25) return '#fa8c16';
  return '#ff4d4f';
}

const COMPONENT_LABELS: Record<string, string> = {
  revenue_growth: 'Revenue Growth',
  customer_health: 'Customer Health',
  operational_efficiency: 'Operations',
  growth_momentum: 'Momentum',
};

export default function HealthScoreCard({ score }: Props) {
  if (!score) return null;

  const color = scoreColor(score.overall_score);

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <HeartOutlined style={{ marginRight: 8, color }} />
        <h3 className={styles.title}>Business Health</h3>
      </div>

      <div className={styles.scoreRow}>
        <Progress
          type="dashboard"
          percent={Math.round(score.overall_score)}
          strokeColor={color}
          size={90}
          format={(pct) => <span className={styles.scoreValue}>{pct}</span>}
        />
        <div className={styles.labelWrap}>
          <span className={styles.label} style={{ color }}>{score.label}</span>
        </div>
      </div>

      <div className={styles.components}>
        {Object.entries(score.components).map(([key, comp]) => (
          <div key={key} className={styles.compRow}>
            <span className={styles.compLabel}>{COMPONENT_LABELS[key] || key}</span>
            <div className={styles.compBar}>
              <Progress
                percent={Math.round(comp.score)}
                size="small"
                strokeColor={scoreColor(comp.score)}
                showInfo={false}
              />
            </div>
            <span className={styles.compScore}>{Math.round(comp.score)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
