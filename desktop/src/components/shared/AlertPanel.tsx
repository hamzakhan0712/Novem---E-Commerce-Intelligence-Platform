import { useState, useEffect, useCallback } from 'react';
import {
  Badge,
  Button,
  Empty,
  Popover,
  Spin,
  Tabs,
  Tag,
  Tooltip,
} from 'antd';
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useAlertData } from '@/hooks/useAlertData';
import { useAlertStore } from '@/stores/alertStore';
import { useStoreStore } from '@/stores/storeStore';
import type { Alert } from '@/types/alerts';

import styles from './AlertPanel.module.css';

const SEVERITY_CONFIG: Record<string, { color: string; icon: React.ReactNode; border: string }> = {
  info: { color: 'blue', icon: <InfoCircleOutlined />, border: '#1677ff' },
  warning: { color: 'orange', icon: <WarningOutlined />, border: '#fa8c16' },
  error: { color: 'red', icon: <CloseCircleOutlined />, border: '#ff4d4f' },
  critical: { color: 'magenta', icon: <ExclamationCircleOutlined />, border: '#eb2f96' },
};

function formatTimeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

export default function AlertPanel() {
  const [open, setOpen] = useState(false);
  const { alerts, unreadCount, loading } = useAlertData();
  const markRead = useAlertStore((s) => s.markRead);
  const markAllRead = useAlertStore((s) => s.markAllRead);
  const deleteAlert = useAlertStore((s) => s.deleteAlert);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);

  interface SyncEvent { data_type: string; source: string; row_count: number; status: string; synced_at: string }
  const [syncHistory, setSyncHistory] = useState<SyncEvent[]>([]);
  const [syncLoading, setSyncLoading] = useState(false);

  const fetchSyncHistory = useCallback(async () => {
    if (!activeStoreId) return;
    setSyncLoading(true);
    try {
      const res = await apiClient.get(`/sync/history/${activeStoreId}`);
      setSyncHistory(res.data?.data ?? []);
    } catch {
      setSyncHistory([]);
    } finally {
      setSyncLoading(false);
    }
  }, [activeStoreId]);

  useEffect(() => {
    if (open) fetchSyncHistory();
  }, [open, fetchSyncHistory]);

  const handleOpenChange = (visible: boolean) => {
    setOpen(visible);
    if (visible) {
      const unreadIds = alerts.filter((a) => !a.is_read).map((a) => a.id);
      if (unreadIds.length > 0) markRead(unreadIds);
    }
  };

  const renderAlertCard = (alert: Alert) => {
    const config = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info;
    return (
      <div
        key={alert.id}
        className={`${styles.card} ${!alert.is_read ? styles.cardUnread : ''}`}
        style={{ borderLeftColor: config.border }}
      >
        <div className={styles.cardHeader}>
          <span className={styles.cardIcon} style={{ color: config.border }}>{config.icon}</span>
          <span className={styles.cardTitle}>{alert.title}</span>
          <Tag color={config.color} className={styles.severityTag}>{alert.severity}</Tag>
          <button className={styles.cardDelete} onClick={() => deleteAlert(alert.id)}>
            <DeleteOutlined />
          </button>
        </div>
        <div className={styles.cardBody}>{alert.message}</div>
        <div className={styles.cardTime}>{formatTimeAgo(alert.created_at)}</div>
      </div>
    );
  };

  const renderSyncCard = (item: SyncEvent, idx: number) => {
    const color = item.status === 'completed' ? '#52c41a' : item.status === 'running' ? '#1677ff' : '#ff4d4f';
    return (
      <div key={idx} className={styles.card} style={{ borderLeftColor: color }}>
        <div className={styles.cardHeader}>
          <SyncOutlined spin={item.status === 'running'} style={{ color }} />
          <span className={styles.cardTitle} style={{ textTransform: 'capitalize' }}>{item.data_type}</span>
          <Tag color={item.status === 'completed' ? 'success' : item.status === 'running' ? 'processing' : 'error'}>
            {item.status}
          </Tag>
        </div>
        <div className={styles.cardBody}>
          {item.row_count > 0 ? `${item.row_count} rows` : ''} via {item.source}
        </div>
        <div className={styles.cardTime}>{formatTimeAgo(item.synced_at)}</div>
      </div>
    );
  };

  const content = (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <span className={styles.panelTitle}>Notifications</span>
        {alerts.length > 0 && (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={() => markAllRead(null)}
          >
            Mark all read
          </Button>
        )}
      </div>
      <Tabs
        defaultActiveKey="alerts"
        size="small"
        className={styles.panelTabs}
        items={[
          {
            key: 'alerts',
            label: `Alerts (${alerts.length})`,
            children: loading ? (
              <div className={styles.loadingCenter}><Spin size="small" /></div>
            ) : alerts.length === 0 ? (
              <Empty description="No alerts" image={Empty.PRESENTED_IMAGE_SIMPLE} className={styles.panelEmpty} />
            ) : (
              <div className={styles.cardList}>
                {alerts.slice(0, 20).map(renderAlertCard)}
              </div>
            ),
          },
          {
            key: 'sync',
            label: <span><SyncOutlined spin={syncLoading} /> Activity</span>,
            children: syncLoading ? (
              <div className={styles.loadingCenter}><Spin size="small" /></div>
            ) : syncHistory.length === 0 ? (
              <Empty description="No sync activity" image={Empty.PRESENTED_IMAGE_SIMPLE} className={styles.panelEmpty} />
            ) : (
              <div className={styles.cardList}>
                {syncHistory.slice(0, 20).map(renderSyncCard)}
              </div>
            ),
          },
        ]}
      />
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={handleOpenChange}
      placement="bottomRight"
      arrow={false}
      overlayClassName={styles.popoverOverlay}
    >
      <Tooltip title={open ? undefined : 'Notifications'}>
        <Badge count={unreadCount} size="small" offset={[-2, 2]}>
          <button className={styles.bellButton}>
            <BellOutlined />
          </button>
        </Badge>
      </Tooltip>
    </Popover>
  );
}
