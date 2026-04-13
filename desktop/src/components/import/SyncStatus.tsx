import { useEffect, useState, useRef } from 'react';

import { Button, Table, Tag, message } from 'antd';
import { SyncOutlined, PlayCircleOutlined } from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

import styles from './SyncStatus.module.css';

interface SyncSchedule {
  id: string;
  connector_type: string;
  data_types: string[];
  interval_minutes: number;
  is_active: boolean;
  last_sync_at: string | null;
  last_sync_status: string | null;
  next_sync_at: string | null;
}

interface SyncHistoryItem {
  id: string;
  data_type: string;
  source_type: string;
  row_count_raw: number;
  status: string;
  imported_at: string;
}

export default function SyncStatus() {
  const [schedules, setSchedules] = useState<SyncSchedule[]>([]);
  const [history, setHistory] = useState<SyncHistoryItem[]>([]);
  const [syncing, setSyncing] = useState(false);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const startGlobalSync = useSyncStore((s) => s.startSync);
  const endGlobalSync = useSyncStore((s) => s.endSync);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = () => {
    if (!activeStoreId) return;
    apiClient.get(`/sync/schedules/${activeStoreId}`).then((res) => {
      setSchedules(res.data?.data ?? []);
    }).catch(() => {});
    apiClient.get(`/sync/history/${activeStoreId}`).then((res) => {
      setHistory(res.data?.data ?? []);
    }).catch(() => {});
  };

  useEffect(() => {
    loadData();
    // Auto-refresh every 10 seconds to detect new sync results
    pollRef.current = setInterval(loadData, 10000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [activeStoreId]);

  const handleSyncNow = async () => {
    if (!activeStoreId) return;
    setSyncing(true);
    startGlobalSync('Triggering manual sync…');
    try {
      await apiClient.post(`/sync/trigger/${activeStoreId}`);
      message.info('Sync triggered — results will appear in the history below');
      loadData();
    } catch {
      message.error('Sync trigger failed');
    } finally {
      setSyncing(false);
      endGlobalSync();
    }
  };

  const activeSchedule = schedules.find((s) => s.is_active);

  if (!activeSchedule && history.length === 0) {
    return null;
  }

  return (
    <div className={styles.syncStatus}>
      <div className={styles.syncHeader}>
        <SyncOutlined spin={syncing} style={{ fontSize: 24, color: 'var(--novem-accent)' }} />
        <div>
          <h3 className={styles.syncTitle}>Sync Status</h3>
          <span className={styles.syncDesc}>Automatic data synchronization</span>
        </div>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleSyncNow}
          loading={syncing}
          disabled={!activeSchedule}
          style={{ marginLeft: 'auto' }}
        >
          Sync Now
        </Button>
      </div>

      {activeSchedule && (
        <div className={styles.syncOverview}>
          <div className={styles.syncStat}>
            <span className={styles.syncStatLabel}>Connector</span>
            <span className={styles.syncStatValue}>{activeSchedule.connector_type.replace('_api', '').replace('_', ' ')}</span>
          </div>
          <div className={styles.syncStat}>
            <span className={styles.syncStatLabel}>Frequency</span>
            <span className={styles.syncStatValue}>
              {activeSchedule.interval_minutes >= 60
                ? `${activeSchedule.interval_minutes / 60}h`
                : `${activeSchedule.interval_minutes}m`}
            </span>
          </div>
          <div className={styles.syncStat}>
            <span className={styles.syncStatLabel}>Last Sync</span>
            <span className={styles.syncStatValue}>
              {activeSchedule.last_sync_at ? new Date(activeSchedule.last_sync_at).toLocaleString() : 'Never'}
            </span>
          </div>
          <div className={styles.syncStat}>
            <span className={styles.syncStatLabel}>Status</span>
            <span className={styles.syncStatValue}>
              <Tag color={activeSchedule.last_sync_status === 'completed' ? 'green' : activeSchedule.last_sync_status === 'partial_error' ? 'orange' : 'default'}>
                {activeSchedule.last_sync_status || 'Pending'}
              </Tag>
            </span>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className={styles.historyTable}>
          <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0', color: 'var(--novem-text-primary)' }}>Sync History</h4>
          <Table
            size="small"
            dataSource={history}
            rowKey="id"
            pagination={{ pageSize: 10, size: 'small' }}
            columns={[
              { title: 'Data Type', dataIndex: 'data_type', key: 'data_type' },
              { title: 'Source', dataIndex: 'source_type', key: 'source_type' },
              { title: 'Rows', dataIndex: 'row_count_raw', key: 'row_count_raw' },
              {
                title: 'Status',
                dataIndex: 'status',
                key: 'status',
                render: (s: string) => <Tag color={s === 'completed' ? 'green' : 'red'}>{s}</Tag>,
              },
              {
                title: 'Time',
                dataIndex: 'imported_at',
                key: 'imported_at',
                render: (d: string) => new Date(d).toLocaleString(),
              },
            ]}
          />
        </div>
      )}
    </div>
  );
}
