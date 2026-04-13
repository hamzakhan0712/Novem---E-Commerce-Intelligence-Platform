import { useState, useEffect } from 'react';

import { Table, Tag, Select } from 'antd';
import {
  BookOutlined,
  CheckCircleFilled,
  MinusCircleOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';

import type { SchemaReferenceResponse, SchemaColumnInfo, DataType } from '@/types/ingestion';

import styles from './SchemaReferencePanel.module.css';

const DATA_TYPE_OPTIONS: { value: DataType; label: string }[] = [
  { value: 'orders', label: 'Orders' },
  { value: 'customers', label: 'Customers' },
  { value: 'products', label: 'Products' },
  { value: 'ad_spend', label: 'Ad Spend' },
  { value: 'reviews', label: 'Reviews' },
  { value: 'stock_levels', label: 'Stock Levels' },
];

interface Props {
  dataType?: DataType;
}

export default function SchemaReferencePanel({ dataType }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [selectedType, setSelectedType] = useState<DataType>(dataType ?? 'orders');
  const [schema, setSchema] = useState<SchemaReferenceResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (dataType) setSelectedType(dataType);
  }, [dataType]);

  useEffect(() => {
    if (!expanded) return;
    setLoading(true);
    apiClient
      .get<{ success: boolean; data: SchemaReferenceResponse }>(
        `/ingestion/schema-reference/${selectedType}`,
      )
      .then((res) => {
        if (res.data.success && res.data.data) {
          setSchema(res.data.data);
        }
      })
      .catch(() => { /* non-critical */ })
      .finally(() => setLoading(false));
  }, [selectedType, expanded]);

  const columns = [
    {
      title: 'Column',
      dataIndex: 'column',
      key: 'column',
      render: (v: string) => <code className={styles.colName}>{v}</code>,
    },
    {
      title: 'Required',
      dataIndex: 'required',
      key: 'required',
      width: 80,
      render: (v: boolean) =>
        v ? (
          <CheckCircleFilled style={{ color: 'var(--novem-error)', fontSize: 14 }} />
        ) : (
          <MinusCircleOutlined style={{ color: 'var(--novem-text-tertiary)', fontSize: 14 }} />
        ),
    },
    {
      title: 'Type',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 80,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'Default',
      dataIndex: 'default_value',
      key: 'default_value',
      width: 90,
      render: (v: string | null) =>
        v ? <span className={styles.defaultVal}>{v}</span> : <span className={styles.noDefault}>—</span>,
    },
    {
      title: 'Example',
      dataIndex: 'example',
      key: 'example',
      render: (v: string) => <span className={styles.example}>{v}</span>,
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes',
      render: (v: string) => <span className={styles.notes}>{v}</span>,
    },
  ];

  return (
    <div className={styles.container}>
      <button className={styles.toggle} onClick={() => setExpanded(!expanded)}>
        <BookOutlined className={styles.toggleIcon} />
        <span className={styles.toggleLabel}>Schema Reference</span>
        <span className={styles.toggleHint}>
          {expanded ? 'Hide' : 'Show'} expected columns for each data type
        </span>
        <span className={styles.chevron}>{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && (
        <div className={styles.panel}>
          <div className={styles.typeSelector}>
            <span className={styles.typeSelectorLabel}>Data type:</span>
            <Select
              size="small"
              value={selectedType}
              onChange={setSelectedType}
              options={DATA_TYPE_OPTIONS}
              style={{ width: 140 }}
            />
          </div>
          <Table<SchemaColumnInfo>
            dataSource={schema?.columns ?? []}
            columns={columns}
            rowKey="column"
            loading={loading}
            size="small"
            pagination={false}
            className={styles.table}
          />
        </div>
      )}
    </div>
  );
}
