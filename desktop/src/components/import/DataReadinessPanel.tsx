import { useState, useEffect } from 'react';

import { Tag } from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  WarningFilled,
  DashboardOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

import type { FeatureReadiness } from '@/types/ingestion';

import styles from './DataReadinessPanel.module.css';

const STATUS_CONFIG = {
  ready: { icon: <CheckCircleFilled style={{ color: 'var(--novem-success)' }} />, color: 'success' as const, label: 'Ready' },
  warning: { icon: <WarningFilled style={{ color: 'var(--novem-warning)' }} />, color: 'warning' as const, label: 'Partial' },
  not_ready: { icon: <CloseCircleFilled style={{ color: 'var(--novem-error)' }} />, color: 'error' as const, label: 'Not Ready' },
};

export default function DataReadinessPanel() {
  const [features, setFeatures] = useState<FeatureReadiness[]>([]);
  const [loading, setLoading] = useState(false);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);

  useEffect(() => {
    if (!activeStoreId) return;
    setLoading(true);
    apiClient
      .get<{ success: boolean; data: { features: FeatureReadiness[] } }>(
        `/ingestion/data-readiness?store_id=${encodeURIComponent(activeStoreId)}`,
      )
      .then((res) => {
        if (res.data.success && res.data.data) {
          setFeatures(res.data.data.features);
        }
      })
      .catch(() => { /* non-critical */ })
      .finally(() => setLoading(false));
  }, [activeStoreId]);

  if (!activeStoreId || loading || features.length === 0) return null;

  const readyCount = features.filter((f) => f.status === 'ready').length;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <DashboardOutlined className={styles.headerIcon} />
        <div className={styles.headerText}>
          <span className={styles.title}>Feature Readiness</span>
          <span className={styles.subtitle}>
            {readyCount}/{features.length} features ready with current data
          </span>
        </div>
      </div>
      <div className={styles.grid}>
        {features.map((f) => {
          const cfg = STATUS_CONFIG[f.status] ?? STATUS_CONFIG.not_ready;
          return (
            <div key={f.feature} className={styles.featureCard} data-status={f.status}>
              <div className={styles.featureHeader}>
                {cfg.icon}
                <span className={styles.featureName}>{f.feature}</span>
                <Tag color={cfg.color} className={styles.featureTag}>{cfg.label}</Tag>
              </div>
              <span className={styles.featureDesc}>{f.description}</span>
              <div className={styles.featureMeta}>
                <span className={styles.featureMetaLabel}>Need:</span>
                <span>{f.minimum_required}</span>
              </div>
              <div className={styles.featureMeta}>
                <span className={styles.featureMetaLabel}>Have:</span>
                <span>{f.current_value}</span>
              </div>
              {f.status !== 'ready' && (
                <span className={styles.featureDetail}>{f.detail}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
