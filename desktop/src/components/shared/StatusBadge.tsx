import styles from './StatusBadge.module.css';

interface StatusBadgeProps {
  status: string;
  label: string;
  size?: 'sm' | 'md';
}

const STATUS_COLORS: Record<string, string> = {
  healthy: styles.green,
  completed: styles.green,
  champions: styles.green,
  reorder_soon: styles.amber,
  promising: styles.amber,
  pending: styles.amber,
  stockout_risk: styles.red,
  at_risk: styles.red,
  refunded: styles.red,
  dead_stock: styles.gray,
  lost: styles.gray,
  cancelled: styles.gray,
};

export function StatusBadge({ status, label, size = 'md' }: StatusBadgeProps) {
  const colorClass = STATUS_COLORS[status] ?? styles.gray;

  return (
    <span className={`${styles.badge} ${colorClass} ${styles[size]}`}>
      {label}
    </span>
  );
}
