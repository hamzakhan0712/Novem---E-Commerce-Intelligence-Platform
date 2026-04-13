import { useState, useEffect, useCallback } from 'react';

import { Empty, Spin, Tag } from 'antd';
import { BulbOutlined, RightOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';
import { useDashboardStore } from '@/stores/dashboardStore';
import { ROUTES } from '@/constants/routes';

import styles from './QuickInsightsCard.module.css';

interface InsightSummary {
  total_insights: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  anomaly_count: number;
  action_count: number;
}

interface InsightItem {
  type: string;
  severity: string;
  title: string;
  message: string;
  priority: number;
}

const SEVERITY_COLOR: Record<string, string> = {
  negative: 'red',
  warning: 'orange',
  positive: 'green',
  info: 'blue',
};

export default function QuickInsightsCard() {
  const navigate = useNavigate();
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const period = useDashboardStore((s) => s.period);
  const [summary, setSummary] = useState<InsightSummary | null>(null);
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!activeStoreId) return;
    setLoading(true);
    try {
      const [summaryRes, insightsRes] = await Promise.all([
        apiClient.get(`/insights/summary?store_id=${encodeURIComponent(activeStoreId)}&period=${period}`),
        apiClient.get(`/insights?store_id=${encodeURIComponent(activeStoreId)}&period=${period}`),
      ]);
      setSummary(summaryRes.data?.data ?? null);
      const all: InsightItem[] = insightsRes.data?.data ?? [];
      setInsights(all.slice(0, 3));
    } catch {
      setSummary(null);
      setInsights([]);
    } finally {
      setLoading(false);
    }
  }, [activeStoreId, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData, lastSyncTick]);

  if (loading) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <BulbOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>Quick Insights</span>
        </div>
        <div className={styles.loadingCenter}><Spin size="small" /></div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <BulbOutlined className={styles.headerIcon} />
        <span className={styles.headerTitle}>Quick Insights</span>
        <button className={styles.viewAll} onClick={() => navigate(ROUTES.INSIGHTS)}>
          View all
        </button>
      </div>

      {summary && (
        <div className={styles.counters}>
          <div className={`${styles.counter} ${styles.counterCritical}`}>
            <span className={styles.counterValue}>{summary.critical_count}</span>
            <span className={styles.counterLabel}>Critical</span>
          </div>
          <div className={`${styles.counter} ${styles.counterWarning}`}>
            <span className={styles.counterValue}>{summary.warning_count}</span>
            <span className={styles.counterLabel}>Warnings</span>
          </div>
          <div className={`${styles.counter} ${styles.counterAnomaly}`}>
            <span className={styles.counterValue}>{summary.anomaly_count}</span>
            <span className={styles.counterLabel}>Unusual</span>
          </div>
          <div className={`${styles.counter} ${styles.counterAction}`}>
            <span className={styles.counterValue}>{summary.action_count}</span>
            <span className={styles.counterLabel}>Actions</span>
          </div>
        </div>
      )}

      {insights.length === 0 ? (
        <Empty description="No insights yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className={styles.list}>
          {insights.map((item, i) => (
            <div key={i} className={styles.insightRow} onClick={() => navigate(ROUTES.INSIGHTS)}>
              <div className={styles.insightContent}>
                <div className={styles.insightHeader}>
                  <Tag color={SEVERITY_COLOR[item.severity] ?? 'default'} className={styles.tag}>
                    {item.severity}
                  </Tag>
                  <span className={styles.insightType}>{item.type}</span>
                </div>
                <span className={styles.insightTitle}>{item.title}</span>
              </div>
              <RightOutlined className={styles.chevron} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
