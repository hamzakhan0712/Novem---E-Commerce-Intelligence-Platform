import type { HealthCheckDetail } from '@/types/ingestion';
import { getHealthColor, getHealthTier } from '@/types/ingestion';

import styles from './HealthScoreDisplay.module.css';

interface HealthScoreDisplayProps {
  score: number;
  details: HealthCheckDetail[];
}

export default function HealthScoreDisplay({ score, details }: HealthScoreDisplayProps) {
  const color = getHealthColor(getHealthTier(score));
  const label = score >= 80 ? 'Healthy' : score >= 50 ? 'Needs Review' : 'Poor Quality';

  return (
    <div className={styles.wrap}>
      <div className={styles.scoreRow}>
        <div className={styles.scoreCircle} style={{ borderColor: color }}>
          <span className={styles.scoreValue} style={{ color }}>{score}</span>
        </div>
        <div className={styles.scoreInfo}>
          <span className={styles.scoreLabel} style={{ color }}>{label}</span>
          <span className={styles.scoreDesc}>Data Quality Score</span>
        </div>
      </div>

      <div className={styles.checks}>
        {details.map((d) => (
          <div key={d.check} className={styles.checkRow}>
            <span className={styles.checkName}>{_formatName(d.check)}</span>
            <div className={styles.checkBar}>
              <div
                className={styles.checkFill}
                style={{
                  width: `${d.score}%`,
                  background: getHealthColor(getHealthTier(d.score)),
                }}
              />
            </div>
            <span className={styles.checkScore}>{Math.round(d.score)}</span>
          </div>
        ))}
      </div>

      {details.some((d) => d.issues.length > 0) && (
        <div className={styles.issues}>
          {details
            .filter((d) => d.issues.length > 0)
            .flatMap((d) => d.issues)
            .map((issue, i) => (
              <p key={i} className={styles.issue}>{issue}</p>
            ))}
        </div>
      )}
    </div>
  );
}

function _formatName(check: string): string {
  return check.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
