import type { ReactNode } from 'react';

import { Button } from 'antd';

import styles from './EmptyState.module.css';

function NoDataIllustration() {
  return (
    <svg
      width="160"
      height="120"
      viewBox="0 0 160 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={styles.illustration}
    >
      {/* Base platform */}
      <ellipse cx="80" cy="108" rx="60" ry="8" fill="var(--novem-text-tertiary)" opacity="0.08" />

      {/* Empty box */}
      <rect x="44" y="38" width="72" height="60" rx="6" fill="var(--novem-bg-elevated)" stroke="var(--novem-border-default)" strokeWidth="1.5" />

      {/* Box inner lines (empty rows) */}
      <line x1="56" y1="56" x2="104" y2="56" stroke="var(--novem-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" opacity="0.18" />
      <line x1="56" y1="68" x2="96" y2="68" stroke="var(--novem-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" opacity="0.14" />
      <line x1="56" y1="80" x2="88" y2="80" stroke="var(--novem-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" opacity="0.10" />

      {/* Accent circle with "!" */}
      <circle cx="104" cy="34" r="14" fill="var(--novem-accent)" opacity="0.12" />
      <circle cx="104" cy="34" r="10" fill="var(--novem-accent)" opacity="0.18" />
      <text x="104" y="38" textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--novem-accent)">!</text>

      {/* Small chart bars (faded) */}
      <rect x="22" y="72" width="8" height="24" rx="2" fill="var(--novem-text-tertiary)" opacity="0.06" />
      <rect x="32" y="64" width="8" height="32" rx="2" fill="var(--novem-text-tertiary)" opacity="0.06" />
      <rect x="120" y="68" width="8" height="28" rx="2" fill="var(--novem-text-tertiary)" opacity="0.06" />
      <rect x="130" y="76" width="8" height="20" rx="2" fill="var(--novem-text-tertiary)" opacity="0.06" />
    </svg>
  );
}

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      {icon ?? <NoDataIllustration />}
      <span className={styles.title}>{title}</span>
      {description && <span className={styles.description}>{description}</span>}
      {action && (
        <Button type="primary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
