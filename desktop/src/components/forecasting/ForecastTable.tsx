import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { formatCurrency } from '@/utils/formatCurrency';

import type { ForecastPoint, ForecastMetric } from '@/types/forecasting';

import styles from './ForecastTable.module.css';

interface Props {
  data: ForecastPoint[];
  metric: ForecastMetric;
}

function formatValue(val: number, metric: string): string {
  if (metric === 'revenue' || metric === 'aov') {
    return formatCurrency(val);
  }
  return val.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function getDayOfWeek(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

export default function ForecastTable({ data, metric }: Props) {
  const forecastData = data.filter((p) => p.is_forecast);

  const columns: ColumnsType<ForecastPoint> = [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      render: (v: string) => v.slice(0, 10),
    },
    {
      title: 'Day',
      key: 'day',
      width: 60,
      render: (_, r) => <span className={styles.dayLabel}>{getDayOfWeek(r.date)}</span>,
    },
    {
      title: 'Forecast',
      dataIndex: 'value',
      key: 'value',
      align: 'right',
      width: 130,
      render: (v: number) => <strong>{formatValue(v, metric)}</strong>,
      sorter: (a, b) => a.value - b.value,
    },
    {
      title: 'Lower Bound',
      dataIndex: 'lower',
      key: 'lower',
      align: 'right',
      width: 130,
      render: (v: number | null) => (v != null ? formatValue(v, metric) : '—'),
    },
    {
      title: 'Upper Bound',
      dataIndex: 'upper',
      key: 'upper',
      align: 'right',
      width: 130,
      render: (v: number | null) => (v != null ? formatValue(v, metric) : '—'),
    },
    {
      title: 'Range',
      key: 'range',
      align: 'right',
      width: 130,
      render: (_, r) => {
        if (r.lower == null || r.upper == null) return '—';
        const range = r.upper - r.lower;
        return <span className={styles.rangeValue}>±{formatValue(range / 2, metric)}</span>;
      },
    },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>Daily Forecast Breakdown</span>
        <Tag color="purple">{forecastData.length} days</Tag>
      </div>
      <Table
        dataSource={forecastData}
        columns={columns}
        rowKey="date"
        size="small"
        pagination={{ pageSize: 14, showSizeChanger: true, pageSizeOptions: ['7', '14', '30', '60', '90'] }}
        scroll={{ y: 400 }}
      />
    </div>
  );
}
