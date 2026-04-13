import { useEffect, useState } from 'react';

import { Table, Tag, Empty, Collapse } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  ExperimentOutlined,
  GoogleOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

import type { ColumnsType } from 'antd/es/table';
import type { ApiResponse } from '@/types/api';
import type { ImportHistoryItem, ImportLineageStep } from '@/types/ingestion';
import { getHealthColor, getHealthTier } from '@/types/ingestion';

import styles from './ImportHistory.module.css';

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  file: <FileTextOutlined />,
  sample: <ExperimentOutlined />,
  google_sheets: <GoogleOutlined />,
};

const STATUS_MAP: Record<string, { color: string; icon: React.ReactNode }> = {
  completed: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <CloseCircleOutlined /> },
  pending: { color: 'default', icon: <ClockCircleOutlined /> },
};

function LineageExpand({ importId }: { importId: string }) {
  const [steps, setSteps] = useState<ImportLineageStep[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get<ApiResponse<ImportLineageStep[]>>(`/ingestion/imports/${importId}/lineage`)
      .then((res) => {
        if (res.data.success && res.data.data) setSteps(res.data.data);
      })
      .finally(() => setLoading(false));
  }, [importId]);

  if (loading) return <span className={styles.lineageLoading}>Loading lineage...</span>;
  if (!steps.length) return <span className={styles.lineageEmpty}>No lineage recorded</span>;

  return (
    <Collapse
      size="small"
      items={steps.map((s) => ({
        key: s.id,
        label: (
          <span className={styles.lineageLabel}>
            <Tag color="blue">Step {s.step_order}</Tag>
            {s.description}
          </span>
        ),
        children: (
          <div className={styles.lineageMeta}>
            <span>Rows: {s.rows_before.toLocaleString()} → {s.rows_after.toLocaleString()}</span>
          </div>
        ),
      }))}
    />
  );
}

export default function ImportHistory() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const [imports, setImports] = useState<ImportHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeStoreId) {
      setImports([]);
      return;
    }
    setLoading(true);
    apiClient
      .get<ApiResponse<ImportHistoryItem[]>>(
        `/ingestion/imports?store_id=${encodeURIComponent(activeStoreId)}`,
      )
      .then((res) => {
        if (res.data.success && res.data.data) setImports(res.data.data);
      })
      .catch(() => setImports([]))
      .finally(() => setLoading(false));
  }, [activeStoreId]);

  const columns: ColumnsType<ImportHistoryItem> = [
    {
      title: 'Date',
      dataIndex: 'imported_at',
      key: 'imported_at',
      width: 170,
      render: (v: string) => {
        const d = new Date(v);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      },
    },
    {
      title: 'Source',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (type: string, record) => (
        <span className={styles.sourceCell}>
          {SOURCE_ICONS[type] ?? <FileTextOutlined />}
          <span>{record.source_name ?? type}</span>
        </span>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 100,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'Rows',
      key: 'rows',
      width: 200,
      render: (_, r) => (
        <span className={styles.rowCounts}>
          <span className={styles.rowNew}>+{r.row_count_new.toLocaleString()}</span>
          <span className={styles.rowUpdated}>~{r.row_count_updated.toLocaleString()}</span>
          <span className={styles.rowSkipped}>{r.row_count_skipped.toLocaleString()} skip</span>
        </span>
      ),
    },
    {
      title: 'Quality',
      dataIndex: 'health_score',
      key: 'health_score',
      width: 80,
      render: (score: number) => (
        <span style={{ color: getHealthColor(getHealthTier(score)), fontWeight: 600 }}>{score}%</span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const cfg = STATUS_MAP[status] ?? STATUS_MAP.pending;
        return <Tag icon={cfg.icon} color={cfg.color}>{status}</Tag>;
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 90,
      render: (ms: number | null) => (ms != null ? `${(ms / 1000).toFixed(1)}s` : '—'),
    },
  ];

  if (!activeStoreId) return null;

  return (
    <div className={styles.container}>
      <h3 className={styles.heading}>Import History</h3>
      <Table
        dataSource={imports}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        locale={{ emptyText: <Empty description="No imports yet" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        expandable={{
          expandedRowRender: (record) => <LineageExpand importId={record.id} />,
          rowExpandable: () => true,
        }}
      />
    </div>
  );
}
