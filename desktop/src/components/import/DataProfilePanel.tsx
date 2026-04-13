import { Spin } from 'antd';

import { useDataProfile } from '@/hooks/useDataProfile';

import type { ColumnProfile } from '@/types/ingestion';

import styles from './DataProfilePanel.module.css';

interface DataProfilePanelProps {
  storeId: string;
  dataType: string;
}

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function getDtypeClass(dtype: string): string {
  if (dtype === 'number') return styles.dtypeNumber;
  if (dtype === 'date') return styles.dtypeDate;
  return styles.dtypeString;
}

function ColumnCard({ col, totalRows }: { col: ColumnProfile; totalRows: number }) {
  const maxCount = col.top_values.length > 0
    ? Math.max(...col.top_values.map((tv) => tv.count))
    : 1;

  return (
    <div className={styles.columnCard}>
      <div className={styles.columnHeader}>
        <span className={styles.columnName}>{col.name}</span>
        <span className={`${styles.columnDtype} ${getDtypeClass(col.dtype)}`}>
          {col.dtype}
        </span>
      </div>
      <div className={styles.columnStats}>
        <div className={styles.stat}>
          <span className={styles.statKey}>Unique</span>
          <span className={styles.statVal}>{col.unique_count.toLocaleString()}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statKey}>Nulls</span>
          <span className={styles.statVal}>{col.null_count} ({col.null_pct}%)</span>
        </div>
        {col.min != null && (
          <div className={styles.stat}>
            <span className={styles.statKey}>Min</span>
            <span className={styles.statVal}>{formatNumber(col.min as number)}</span>
          </div>
        )}
        {col.max != null && (
          <div className={styles.stat}>
            <span className={styles.statKey}>Max</span>
            <span className={styles.statVal}>{formatNumber(col.max as number)}</span>
          </div>
        )}
        {col.mean != null && (
          <div className={styles.stat}>
            <span className={styles.statKey}>Mean</span>
            <span className={styles.statVal}>{formatNumber(col.mean)}</span>
          </div>
        )}
        {col.std != null && (
          <div className={styles.stat}>
            <span className={styles.statKey}>Std Dev</span>
            <span className={styles.statVal}>{formatNumber(col.std)}</span>
          </div>
        )}
      </div>
      {col.top_values.length > 0 && (
        <div className={styles.topValues}>
          <div className={styles.topValuesLabel}>Top Values</div>
          {col.top_values.map((tv) => (
            <div key={tv.value} className={styles.topValueBar}>
              <span className={styles.topValueName} title={tv.value}>{tv.value}</span>
              <div className={styles.topValueTrack}>
                <div
                  className={styles.topValueFill}
                  style={{ width: `${(tv.count / maxCount) * 100}%` }}
                />
              </div>
              <span className={styles.topValueCount}>
                {tv.count} ({totalRows > 0 ? ((tv.count / totalRows) * 100).toFixed(1) : 0}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DataProfilePanel({ storeId, dataType }: DataProfilePanelProps) {
  const { data, loading, error } = useDataProfile(storeId, dataType);

  if (!storeId) {
    return (
      <div className={styles.emptyState}>
        Select a dataset to view its profile.
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.emptyState}>
        <Spin size="small" />
        <p>Loading profile…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={styles.emptyState}>
        {error ?? 'No profile data available.'}
      </div>
    );
  }

  return (
    <div className={styles.profilePanel}>
      <div className={styles.statsRow}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{data.row_count.toLocaleString()}</div>
          <div className={styles.statLabel}>Total Rows</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{data.columns.length}</div>
          <div className={styles.statLabel}>Columns</div>
        </div>
        {data.date_range && (
          <div className={styles.statCard}>
            <div className={styles.statValue} style={{ fontSize: 13 }}>
              {new Date(data.date_range.min).toLocaleDateString()} — {new Date(data.date_range.max).toLocaleDateString()}
            </div>
            <div className={styles.statLabel}>Date Range</div>
          </div>
        )}
      </div>

      {data.columns.map((col) => (
        <ColumnCard key={col.name} col={col} totalRows={data.row_count} />
      ))}
    </div>
  );
}
