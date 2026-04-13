import { Select, Tag } from 'antd';
import { CheckCircleFilled, WarningOutlined } from '@ant-design/icons';

import type { ColumnMapping, DataType } from '@/types/ingestion';

import styles from './ColumnMapper.module.css';

const CANONICAL_COLUMNS: Record<DataType, string[]> = {
  orders: [
    'order_id', 'order_date', 'customer_id', 'customer_email_hash',
    'customer_name_hash', 'product_id', 'product_name', 'category',
    'quantity', 'unit_price', 'total_price', 'discount_amount',
    'currency', 'status', 'refund_amount', 'refund_reason',
    'channel', 'region',
  ],
  customers: [
    'customer_id', 'email_hash', 'name_hash', 'first_order_date',
    'last_order_date', 'total_orders', 'total_spend',
    'avg_order_value', 'region',
  ],
  products: [
    'product_id', 'product_name', 'category', 'subcategory',
    'unit_cost', 'current_stock', 'status', 'size', 'color',
  ],
  ad_spend: [
    'date', 'channel', 'campaign_name', 'impressions', 'clicks',
    'spend', 'currency', 'conversions', 'revenue_attributed',
  ],
  reviews: [
    'review_id', 'product_id', 'customer_id', 'review_date',
    'rating', 'review_text',
  ],
  stock_levels: [
    'product_id', 'snapshot_date', 'quantity_on_hand', 'lead_time_days',
  ],
};

interface ColumnMapperProps {
  mappings: ColumnMapping[];
  dataType: DataType;
  sampleRow: (string | number | null)[];
  headers: string[];
  onMappingChange: (index: number, targetColumn: string | null) => void;
}

export default function ColumnMapper({ mappings, dataType, sampleRow, headers: _headers, onMappingChange }: ColumnMapperProps) {
  const canonicalCols = CANONICAL_COLUMNS[dataType] ?? [];
  const usedTargets = new Set(
    mappings.filter((m) => m.target_column).map((m) => m.target_column),
  );

  const mappedCount = mappings.filter((m) => m.target_column).length;
  const totalCanonical = canonicalCols.length;

  return (
    <div className={styles.mapper}>
      <div className={styles.mapperHeader}>
        <span className={styles.mapperTitle}>Column Mapping</span>
        <span className={styles.mapperStatus}>
          {mappedCount}/{totalCanonical} columns mapped
          {mappedCount === totalCanonical && (
            <CheckCircleFilled style={{ color: 'var(--novem-success)', marginLeft: 6 }} />
          )}
        </span>
      </div>

      <div className={styles.mapperGrid}>
        <div className={styles.mapperGridHeader}>
          <span>Source Column</span>
          <span>Sample Value</span>
          <span>Maps To</span>
          <span>Status</span>
        </div>

        {mappings.map((mapping, i) => {
          const sampleValue = sampleRow[i] != null ? String(sampleRow[i]) : '—';
          const isMapped = Boolean(mapping.target_column);

          return (
            <div key={i} className={styles.mapperRow}>
              <span className={styles.sourceCol}>{mapping.source_column}</span>
              <span className={styles.sampleVal} title={sampleValue}>{sampleValue}</span>
              <Select
                size="small"
                allowClear
                showSearch
                placeholder="Skip (unmapped)"
                value={mapping.target_column ?? undefined}
                onChange={(val) => onMappingChange(i, val ?? null)}
                className={styles.targetSelect}
                options={canonicalCols.map((col) => ({
                  value: col,
                  label: col,
                  disabled: usedTargets.has(col) && mapping.target_column !== col,
                }))}
              />
              <span className={styles.statusCell}>
                {isMapped ? (
                  mapping.auto_mapped ? (
                    <Tag color="green" style={{ margin: 0, fontSize: 11 }}>Auto</Tag>
                  ) : (
                    <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>Manual</Tag>
                  )
                ) : (
                  <Tag color="default" style={{ margin: 0, fontSize: 11 }}>Skipped</Tag>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {mappedCount < totalCanonical && (
        <div className={styles.mapperWarning}>
          <WarningOutlined style={{ color: 'var(--novem-warning)' }} />
          <span>
            {totalCanonical - mappedCount} canonical column(s) have no source mapping.
            Missing columns will be filled with NULL values.
          </span>
        </div>
      )}
    </div>
  );
}
