import styles from './HealthBadge.module.css';

interface HealthBadgeProps {
  score: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

function getLevel(score: number): { label: string; className: string } {
  if (score >= 80) return { label: 'Healthy', className: styles.green };
  if (score >= 50) return { label: 'Needs Review', className: styles.amber };
  return { label: 'Poor Quality', className: styles.red };
}

export function HealthBadge({ score, showLabel = false, size = 'md' }: HealthBadgeProps) {
  const { label, className } = getLevel(score);

  return (
    <span className={`${styles.badge} ${className} ${styles[size]}`}>
      <span className={styles.dot} />
      {showLabel && <span className={styles.label}>{label}</span>}
    </span>
  );
}
