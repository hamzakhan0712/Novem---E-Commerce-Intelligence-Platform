import { useState } from 'react';

import { Button, Form, Input, InputNumber, Select, Table, Tabs, Tag, message } from 'antd';
import { DatabaseOutlined, CheckCircleFilled, CloseCircleFilled, DeleteOutlined, PlusOutlined } from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

import type { DataType } from '@/types/ingestion';

import styles from './DatabaseConnector.module.css';

interface TableMapping {
  table: string;
  data_type: DataType;
}

const DATA_TYPE_OPTIONS: { value: DataType; label: string }[] = [
  { value: 'orders', label: 'Orders' },
  { value: 'customers', label: 'Customers' },
  { value: 'products', label: 'Products' },
  { value: 'reviews', label: 'Reviews' },
  { value: 'ad_spend', label: 'Ad Spend' },
  { value: 'stock_levels', label: 'Stock Levels' },
];

export default function DatabaseConnector() {
  const [form] = Form.useForm();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<boolean | null>(null);
  const [importing, setImporting] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [tableMappings, setTableMappings] = useState<TableMapping[]>([]);
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: unknown[][] } | null>(null);
  const [importResults, setImportResults] = useState<{ table: string; status: string; rows?: number; message?: string }[]>([]);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields(['host', 'port', 'database', 'user', 'password']);
      setTesting(true);
      setTestResult(null);
      const res = await apiClient.post('/connectors/test-connection', {
        credential_type: 'postgresql',
        credentials: values,
      });
      const connected = res.data?.data?.connected ?? false;
      setTestResult(connected);

      if (connected) {
        message.success('Database connection successful');
        if (activeStoreId) {
          await apiClient.post('/credentials', {
            store_id: activeStoreId,
            credential_type: 'postgresql',
            credentials: values,
          });
          const tablesRes = await apiClient.get(`/connectors/${activeStoreId}/tables`);
          setTables(tablesRes.data?.data?.tables ?? []);
        }
      } else {
        message.error(res.data?.data?.message || 'Connection failed');
      }
    } catch {
      setTestResult(false);
      message.error('Connection test failed');
    } finally {
      setTesting(false);
    }
  };

  const handleAddTableMapping = () => {
    setTableMappings((prev) => [...prev, { table: '', data_type: 'orders' }]);
  };

  const handleRemoveTableMapping = (index: number) => {
    setTableMappings((prev) => prev.filter((_, i) => i !== index));
  };

  const handleTableMappingChange = (index: number, field: keyof TableMapping, value: string) => {
    setTableMappings((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handlePreviewQuery = async () => {
    if (!activeStoreId) return;
    const query = form.getFieldValue('query');
    if (!query) {
      message.warning('Enter a SQL query');
      return;
    }
    try {
      const res = await apiClient.post(`/connectors/${activeStoreId}/preview-query`, {
        store_id: activeStoreId,
        query,
        limit: 50,
      });
      setPreviewData(res.data?.data ?? null);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || 'Query failed');
    }
  };

  const handleImport = async () => {
    if (!activeStoreId) {
      message.error('Select a store first');
      return;
    }

    // Multi-table import
    if (tableMappings.length > 0) {
      const validMappings = tableMappings.filter((m) => m.table);
      if (validMappings.length === 0) {
        message.warning('Select at least one table');
        return;
      }

      setImporting(true);
      setImportResults([]);
      try {
        const res = await apiClient.post(`/connectors/${activeStoreId}/import-tables`, {
          store_id: activeStoreId,
          tables: validMappings,
        });
        const results = res.data?.data?.results ?? [];
        setImportResults(results);
        const successCount = results.filter((r: { status: string }) => r.status === 'completed').length;
        if (successCount > 0) {
          message.success(`Imported ${successCount} table(s) successfully`);
        }
        if (successCount < validMappings.length) {
          message.warning(`${validMappings.length - successCount} table(s) failed`);
        }
      } catch {
        message.error('Import failed');
      } finally {
        setImporting(false);
      }
      return;
    }

    // Single-table import (legacy)
    setImporting(true);
    try {
      const values = form.getFieldsValue();
      await apiClient.post('/credentials', {
        store_id: activeStoreId,
        credential_type: 'postgresql',
        credentials: {
          ...values,
          table: values.table,
          query: values.query,
        },
      });

      await apiClient.post('/connectors/sync', {
        store_id: activeStoreId,
        data_types: [values.data_type || 'orders'],
      });
      message.success('Database import started');
    } catch {
      message.error('Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className={styles.connectorForm}>
      <div className={styles.connectorHeader}>
        <DatabaseOutlined style={{ fontSize: 24, color: '#1890ff' }} />
        <div>
          <h3 className={styles.connectorTitle}>PostgreSQL Import</h3>
          <span className={styles.connectorDesc}>Connect to an external PostgreSQL database</span>
        </div>
        {testResult !== null && (
          <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            {testResult ? <CheckCircleFilled style={{ color: 'var(--novem-success)' }} /> : <CloseCircleFilled style={{ color: 'var(--novem-error)' }} />}
            {testResult ? 'Connected' : 'Failed'}
          </span>
        )}
      </div>

      <Form form={form} layout="vertical" initialValues={{ port: 5432, data_type: 'orders' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
          <Form.Item name="host" label="Host" rules={[{ required: true }]}>
            <Input placeholder="localhost" />
          </Form.Item>
          <Form.Item name="port" label="Port" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </div>

        <Form.Item name="database" label="Database Name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Form.Item name="user" label="Username" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
        </div>

        <div className={styles.formActions} style={{ marginBottom: 16 }}>
          <Button onClick={handleTestConnection} loading={testing}>
            Test Connection
          </Button>
        </div>

        {testResult && (
          <Tabs
            items={[
              {
                key: 'multi',
                label: 'Select Tables',
                children: (
                  <>
                    <p style={{ fontSize: 12, color: 'var(--novem-text-tertiary)', marginBottom: 12 }}>
                      Map one or more database tables to NOVEM data types. Each table is imported separately.
                    </p>
                    {tableMappings.map((mapping, i) => (
                      <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                        <Select
                          placeholder="Select table"
                          value={mapping.table || undefined}
                          onChange={(val) => handleTableMappingChange(i, 'table', val)}
                          options={tables.map((t) => ({ value: t, label: t }))}
                          showSearch
                          size="small"
                        />
                        <Select
                          value={mapping.data_type}
                          onChange={(val) => handleTableMappingChange(i, 'data_type', val)}
                          options={DATA_TYPE_OPTIONS}
                          size="small"
                        />
                        <Button
                          size="small"
                          icon={<DeleteOutlined />}
                          danger
                          onClick={() => handleRemoveTableMapping(i)}
                        />
                      </div>
                    ))}
                    <Button
                      type="dashed"
                      icon={<PlusOutlined />}
                      onClick={handleAddTableMapping}
                      style={{ marginBottom: 12 }}
                      block
                      size="small"
                    >
                      Add Table
                    </Button>

                    {importResults.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        {importResults.map((r, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
                            <span style={{ fontWeight: 500 }}>{r.table}</span>
                            <Tag color={r.status === 'completed' ? 'success' : r.status === 'skipped' ? 'warning' : 'error'}>
                              {r.status}
                            </Tag>
                            {r.rows !== undefined && <span>{r.rows} rows</span>}
                            {r.message && <span style={{ color: 'var(--novem-text-tertiary)' }}>{r.message}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ),
              },
              {
                key: 'single',
                label: 'Single Table',
                children: (
                  <>
                    <Form.Item name="table" label="Table">
                      <Select
                        placeholder="Select a table"
                        options={tables.map((t) => ({ value: t, label: t }))}
                        showSearch
                      />
                    </Form.Item>
                    <Form.Item name="data_type" label="Import As">
                      <Select options={DATA_TYPE_OPTIONS} />
                    </Form.Item>
                  </>
                ),
              },
              {
                key: 'sql',
                label: 'Custom SQL',
                children: (
                  <>
                    <Form.Item name="query" label="SQL Query">
                      <Input.TextArea rows={4} placeholder="SELECT * FROM orders WHERE ..." />
                    </Form.Item>
                    <Button onClick={handlePreviewQuery} style={{ marginBottom: 12 }}>
                      Preview Results
                    </Button>
                    {previewData && (
                      <div className={styles.previewTable}>
                        <Table
                          size="small"
                          dataSource={previewData.rows.map((row, i) => {
                            const obj: Record<string, unknown> = { key: i };
                            previewData.columns.forEach((col, j) => { obj[col] = row[j]; });
                            return obj;
                          })}
                          columns={previewData.columns.map((col) => ({ title: col, dataIndex: col, key: col, ellipsis: true }))}
                          pagination={false}
                          scroll={{ x: true }}
                        />
                      </div>
                    )}
                  </>
                ),
              },
            ]}
          />
        )}

        <div className={styles.formActions}>
          <Button type="primary" onClick={handleImport} loading={importing} disabled={!activeStoreId || !testResult}>
            Import Data
          </Button>
        </div>
      </Form>
    </div>
  );
}
