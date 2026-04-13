import { useState, useEffect, useCallback } from 'react';

import { Button, App as AntApp, Tag } from 'antd';
import {
  ReloadOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';

import { useStoreStore } from '@/stores/storeStore';
import apiClient from '@/utils/apiClient';
import type { ApiResponse } from '@/types/api';

import styles from './SystemSettings.module.css';

interface SystemInfo {
  data_dir: string;
  duckdb_path: string;
  sqlite_path: string;
  cache_dir: string;
  duckdb_size: number;
  sqlite_size: number;
  cache_size: number;
  total_storage: number;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function SystemSettings() {
  const { message, modal } = AntApp.useApp();
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [tableCounts, setTableCounts] = useState<Record<string, number>>({});
  const [deletingTable, setDeletingTable] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);

  const activeStoreId = useStoreStore((s) => s.activeStoreId);

  const fetchInfo = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<ApiResponse<SystemInfo>>('/settings/system-info');
      if (res.data.success && res.data.data) {
        setInfo(res.data.data);
      }
    } catch {
      message.error('Failed to load system info');
    } finally {
      setLoading(false);
    }
  }, [message]);

  const fetchTableCounts = useCallback(async () => {
    if (!activeStoreId) return;
    try {
      const res = await apiClient.get<ApiResponse<Record<string, number>>>(
        `/data-viewer/tables?store_id=${encodeURIComponent(activeStoreId)}`
      );
      if (res.data.success && res.data.data) {
        setTableCounts(res.data.data);
      }
    } catch {
      /* silent — non-critical */
    }
  }, [activeStoreId]);

  useEffect(() => {
    fetchInfo();
    fetchTableCounts();
  }, [fetchInfo, fetchTableCounts]);

  const handleClearCache = async () => {
    setClearing(true);
    try {
      const res = await apiClient.delete<ApiResponse<{ removed_files: number }>>('/settings/cache');
      if (res.data.success) {
        message.success(`Cache cleared (${res.data.data?.removed_files ?? 0} files removed)`);
        fetchInfo();
      }
    } catch {
      message.error('Failed to clear cache');
    } finally {
      setClearing(false);
    }
  };

  const TABLE_LABELS: Record<string, string> = {
    orders: 'Orders',
    customers: 'Customers',
    products: 'Products',
    ad_spend: 'Ad Spend',
    reviews: 'Reviews',
    stock_levels: 'Stock Levels',
  };

  const handleDeleteTable = (table: string) => {
    if (!activeStoreId) return;
    const count = tableCounts[table] ?? 0;
    modal.confirm({
      title: `Delete all ${TABLE_LABELS[table] ?? table} data?`,
      icon: <ExclamationCircleOutlined />,
      content: `This will permanently delete ${count.toLocaleString()} rows from the ${TABLE_LABELS[table] ?? table} table. This action cannot be undone.`,
      okText: 'Delete',
      okButtonProps: { danger: true },
      onOk: async () => {
        setDeletingTable(table);
        try {
          const res = await apiClient.delete<ApiResponse<{ deleted_rows: number }>>(
            `/data-viewer/table-data?store_id=${encodeURIComponent(activeStoreId)}&table=${table}`
          );
          if (res.data.success) {
            message.success(`${TABLE_LABELS[table]} data deleted (${res.data.data?.deleted_rows ?? 0} rows)`);
            fetchTableCounts();
            fetchInfo();
          }
        } catch {
          message.error(`Failed to delete ${TABLE_LABELS[table]} data`);
        } finally {
          setDeletingTable(null);
        }
      },
    });
  };

  const handleClearAllData = () => {
    if (!activeStoreId) return;
    const totalRows = Object.values(tableCounts).reduce((sum, c) => sum + c, 0);
    modal.confirm({
      title: 'Clear entire database?',
      icon: <WarningOutlined style={{ color: 'var(--novem-color-error, #ff4d4f)' }} />,
      content: `This will permanently delete ALL data (${totalRows.toLocaleString()} rows across ${Object.keys(tableCounts).length} tables) for the current store. This action cannot be undone.`,
      okText: 'Clear All Data',
      okButtonProps: { danger: true },
      onOk: async () => {
        setClearingAll(true);
        try {
          const res = await apiClient.delete<ApiResponse<{ total_deleted: number }>>(
            `/data-viewer/all-data?store_id=${encodeURIComponent(activeStoreId)}`
          );
          if (res.data.success) {
            message.success(`All data cleared (${res.data.data?.total_deleted ?? 0} rows deleted)`);
            fetchTableCounts();
            fetchInfo();
          }
        } catch {
          message.error('Failed to clear database');
        } finally {
          setClearingAll(false);
        }
      },
    });
  };

  return (
    <div>
      <div className={styles.section}>
        <div className={styles.sectionTitle}>
          Storage Usage
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={fetchInfo}
            loading={loading}
            style={{ marginLeft: 8 }}
          >
            Refresh
          </Button>
        </div>

        {info ? (
          <div className={styles.infoGrid}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Total Storage Used</span>
              <span className={styles.infoValue}>{formatBytes(info.total_storage)}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Your Store Data</span>
              <span className={styles.infoValue}>{formatBytes(info.duckdb_size)}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>System Data</span>
              <span className={styles.infoValue}>{formatBytes(info.sqlite_size)}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Temporary Files</span>
              <span className={styles.infoValue}>
                {formatBytes(info.cache_size)}
                <Button
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={handleClearCache}
                  loading={clearing}
                  disabled={info.cache_size === 0}
                  style={{ marginLeft: 8 }}
                >
                  Clear
                </Button>
              </span>
            </div>
          </div>
        ) : (
          <div className={styles.placeholder}>Loading system info…</div>
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>File Paths</div>

        {info ? (
          <div className={styles.infoGrid}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Data Directory</span>
              <span className={styles.pathValue}>{info.data_dir}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Analytics DB</span>
              <span className={styles.pathValue}>{info.duckdb_path}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Metadata DB</span>
              <span className={styles.pathValue}>{info.sqlite_path}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Cache Directory</span>
              <span className={styles.pathValue}>{info.cache_dir}</span>
            </div>
          </div>
        ) : (
          <div className={styles.placeholder}>Loading…</div>
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>About</div>
        <div className={styles.infoGrid}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>App Version</span>
            <span className={styles.infoValue}>0.3.0</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Engine API</span>
            <span className={styles.infoValue}>v0.3.0</span>
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle} style={{ color: 'var(--novem-color-error, #ff4d4f)' }}>
          <WarningOutlined style={{ marginRight: 8 }} />
          Data Management
        </div>

        {activeStoreId ? (
          <>
            <div className={styles.infoGrid}>
              {Object.entries(TABLE_LABELS).map(([table, label]) => {
                const count = tableCounts[table] ?? 0;
                return (
                  <div className={styles.infoRow} key={table}>
                    <span className={styles.infoLabel}>
                      {label}
                      <Tag
                        style={{ marginLeft: 8, fontSize: 11 }}
                        color={count > 0 ? undefined : 'default'}
                      >
                        {count.toLocaleString()} rows
                      </Tag>
                    </span>
                    <span className={styles.infoValue}>
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDeleteTable(table)}
                        loading={deletingTable === table}
                        disabled={count === 0}
                      >
                        Delete
                      </Button>
                    </span>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--novem-border-default)' }}>
              <Button
                danger
                type="primary"
                icon={<DeleteOutlined />}
                onClick={handleClearAllData}
                loading={clearingAll}
                disabled={Object.values(tableCounts).every((c) => c === 0)}
              >
                Clear All Data
              </Button>
              <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--novem-text-tertiary)' }}>
                Permanently deletes all imported data for the current store. This action cannot be undone.
              </p>
            </div>
          </>
        ) : (
          <div className={styles.placeholder}>Select a store to manage data</div>
        )}
      </div>
    </div>
  );
}
