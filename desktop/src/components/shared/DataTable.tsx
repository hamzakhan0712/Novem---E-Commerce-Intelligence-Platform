import { Table, Button } from 'antd';
import type { TableProps } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

import styles from './DataTable.module.css';

interface DataTableProps<T extends object> extends Omit<TableProps<T>, 'locale'> {
  exportable?: boolean;
  exportFilename?: string;
  emptyText?: string;
}

function exportToCsv<T extends object>(data: readonly T[], columns: TableProps<T>['columns'], filename: string) {
  if (!columns || data.length === 0) return;

  const headers = columns
    .filter((c): c is { title: string; dataIndex: string } => 'dataIndex' in c && typeof c.title === 'string')
    .map((c) => c.title);

  const dataIndexes = columns
    .filter((c): c is { dataIndex: string } => 'dataIndex' in c)
    .map((c) => c.dataIndex);

  const rows = data.map((row) =>
    dataIndexes.map((key) => {
      const val = (row as Record<string, unknown>)[key];
      const str = val == null ? '' : String(val);
      return str.includes(',') || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str;
    }).join(','),
  );

  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function DataTable<T extends object>({
  exportable = false,
  exportFilename = 'export',
  emptyText = 'No data available',
  columns,
  dataSource,
  ...rest
}: DataTableProps<T>) {
  return (
    <div className={styles.wrapper}>
      {exportable && dataSource && dataSource.length > 0 && (
        <div className={styles.toolbar}>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => exportToCsv(dataSource, columns, exportFilename)}
          >
            Export CSV
          </Button>
        </div>
      )}
      <Table<T>
        columns={columns}
        dataSource={dataSource}
        size="small"
        locale={{ emptyText }}
        scroll={{ x: 'max-content' }}
        {...rest}
      />
    </div>
  );
}
