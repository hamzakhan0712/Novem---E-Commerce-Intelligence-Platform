import { useEffect, useState } from 'react';

import { Table, Button, Empty, message, Modal, Tag } from 'antd';
import { UndoOutlined, DeleteOutlined } from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

import type { ColumnsType } from 'antd/es/table';
import type { ApiResponse } from '@/types/api';

import styles from './ImportHistory.module.css';

interface Snapshot {
  snapshot_id: string;
  data_type: string;
  import_id: string;
  row_count: number;
  created_at: string;
}

export default function RollbackPanel() {
  const storeId = useStoreStore((s) => s.activeStoreId);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [rolling, setRolling] = useState(false);

  const fetchSnapshots = () => {
    if (!storeId) return;
    setLoading(true);
    apiClient
      .get<ApiResponse<Snapshot[]>>('/ingestion/snapshots', { params: { store_id: storeId } })
      .then((res) => {
        if (res.data.success && res.data.data) setSnapshots(res.data.data);
      })
      .catch(() => message.error('Failed to load snapshots'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSnapshots(); }, [storeId]);

  const handleRollback = (snap: Snapshot) => {
    Modal.confirm({
      title: 'Confirm Rollback',
      content: `This will restore your ${snap.data_type} data to the state before import (${snap.row_count} rows). Current data will be overwritten. This cannot be undone.`,
      okText: 'Rollback',
      okType: 'danger',
      onOk: async () => {
        setRolling(true);
        try {
          const res = await apiClient.post<ApiResponse<{ rows_after_rollback: number }>>(
            '/ingestion/rollback',
            null,
            { params: { store_id: storeId, snapshot_id: snap.snapshot_id } },
          );
          if (res.data.success) {
            message.success(`Rolled back ${snap.data_type} to ${snap.row_count} rows`);
            fetchSnapshots();
          }
        } catch {
          message.error('Rollback failed');
        } finally {
          setRolling(false);
        }
      },
    });
  };

  const handleDelete = async (snapId: string) => {
    try {
      await apiClient.delete('/ingestion/snapshots', {
        params: { store_id: storeId, snapshot_id: snapId },
      });
      setSnapshots((prev) => prev.filter((s) => s.snapshot_id !== snapId));
      message.success('Snapshot deleted');
    } catch {
      message.error('Failed to delete snapshot');
    }
  };

  const columns: ColumnsType<Snapshot> = [
    {
      title: 'Data Type',
      dataIndex: 'data_type',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'Rows',
      dataIndex: 'row_count',
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, snap: Snapshot) => (
        <span style={{ display: 'flex', gap: 8 }}>
          <Button
            size="small"
            icon={<UndoOutlined />}
            loading={rolling}
            onClick={() => handleRollback(snap)}
          >
            Rollback
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(snap.snapshot_id)}
          />
        </span>
      ),
    },
  ];

  if (!storeId) return null;

  return (
    <div>
      {snapshots.length === 0 ? (
        <Empty description="No import snapshots yet. Snapshots are created automatically before each import." />
      ) : (
        <Table
          dataSource={snapshots}
          columns={columns}
          rowKey="snapshot_id"
          size="small"
          loading={loading}
          pagination={false}
        />
      )}
    </div>
  );
}
