import type { DataPreview } from '@/types/ingestion';

import styles from './DataPreviewTable.module.css';

interface DataPreviewTableProps {
  preview: DataPreview;
}

export default function DataPreviewTable({ preview }: DataPreviewTableProps) {
  return (
    <div className={styles.previewWrap}>
      <table className={styles.previewTable}>
        <thead>
          <tr>
            {preview.headers.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>{cell != null ? String(cell) : ''}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className={styles.rowCount}>
        Showing {preview.rows.length} of {preview.total_rows.toLocaleString()} rows
      </p>
    </div>
  );
}
