import { useState, useEffect, useCallback } from 'react';

import { Button, Empty, message, Popconfirm, Spin, Tag } from 'antd';
import {
  DeleteOutlined, PlayCircleOutlined, ShopOutlined, DatabaseOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

import styles from './SavedConnectors.module.css';

interface SavedCredential {
  id: string;
  store_id: string;
  credential_type: string;
  created_at: string;
  updated_at: string | null;
}

const TYPE_META: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  shopify_api: { icon: <ShopOutlined />, label: 'Shopify', color: '#96bf48' },
  postgresql: { icon: <DatabaseOutlined />, label: 'PostgreSQL', color: '#336791' },
  google_sheets_api: { icon: <DatabaseOutlined />, label: 'Google Sheets', color: '#34a853' },
};

export default function SavedConnectors() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const startGlobalSync = useSyncStore((s) => s.startSync);
  const endGlobalSync = useSyncStore((s) => s.endSync);
  const [credentials, setCredentials] = useState<SavedCredential[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);

  const fetchCredentials = useCallback(async () => {
    if (!activeStoreId) return;
    setLoading(true);
    try {
      const res = await apiClient.get(`/credentials/${activeStoreId}`);
      setCredentials(res.data?.data ?? []);
    } catch {
      setCredentials([]);
    } finally {
      setLoading(false);
    }
  }, [activeStoreId]);

  useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  const handleQuickSync = async (cred: SavedCredential) => {
    if (!activeStoreId) return;
    setSyncing(cred.id);
    const label = TYPE_META[cred.credential_type]?.label ?? cred.credential_type;
    startGlobalSync(`Syncing ${label} data…`);
    try {
      await apiClient.post('/connectors/sync', {
        store_id: activeStoreId,
        data_types: ['orders', 'customers', 'products'],
      });
      message.info(`${label} sync initiated — check Sync Status below for progress`);
    } catch {
      message.error('Sync failed');
    } finally {
      setSyncing(null);
      endGlobalSync();
    }
  };

  const handleDelete = async (credId: string) => {
    try {
      await apiClient.delete(`/credentials/${credId}`);
      message.success('Connector removed');
      fetchCredentials();
    } catch {
      message.error('Failed to remove connector');
    }
  };

  if (!activeStoreId) return null;

  const syncable = credentials.filter((c) => c.credential_type === 'shopify_api' || c.credential_type === 'postgresql');

  if (loading) return <Spin size="small" />;
  if (syncable.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No saved connectors yet" />;

  return (
    <div className={styles.list}>
      {syncable.map((cred) => {
        const meta = TYPE_META[cred.credential_type] ?? { icon: <DatabaseOutlined />, label: cred.credential_type, color: '#999' };
        return (
          <div key={cred.id} className={styles.card}>
            <div className={styles.cardIcon} style={{ color: meta.color }}>
              {meta.icon}
            </div>
            <div className={styles.cardInfo}>
              <span className={styles.cardLabel}>{meta.label}</span>
              <Tag color="green" style={{ fontSize: 10 }}>Connected</Tag>
            </div>
            <div className={styles.cardActions}>
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                loading={syncing === cred.id}
                onClick={() => handleQuickSync(cred)}
              >
                Sync
              </Button>
              <Popconfirm title="Remove this connector?" onConfirm={() => handleDelete(cred.id)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </div>
          </div>
        );
      })}
    </div>
  );
}
