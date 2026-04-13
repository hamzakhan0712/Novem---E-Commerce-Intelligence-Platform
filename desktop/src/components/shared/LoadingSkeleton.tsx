import { Skeleton } from 'antd';

import styles from './LoadingSkeleton.module.css';

interface LoadingSkeletonProps {
  variant: 'card-grid' | 'table' | 'chart' | 'kpi-row';
  rows?: number;
  count?: number;
}

export function LoadingSkeleton({ variant, rows = 5, count = 4 }: LoadingSkeletonProps) {
  if (variant === 'kpi-row') {
    return (
      <div className={styles.kpiRow}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className={styles.kpiSkeleton}>
            <Skeleton.Input active size="small" style={{ width: 80 }} />
            <Skeleton.Input active size="large" style={{ width: 120 }} />
            <Skeleton.Input active size="small" style={{ width: 60 }} />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'card-grid') {
    return (
      <div className={styles.cardGrid}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className={styles.cardSkeleton}>
            <Skeleton active paragraph={{ rows: 3 }} />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className={styles.chartSkeleton}>
        <div className={styles.chartBar} />
      </div>
    );
  }

  // table
  return (
    <div className={styles.tableSkeleton}>
      <Skeleton active paragraph={{ rows }} />
    </div>
  );
}
