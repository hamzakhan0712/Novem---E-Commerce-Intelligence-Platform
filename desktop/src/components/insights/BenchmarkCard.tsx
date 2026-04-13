import { Card, Table, Tag, Spin, Empty } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { useBenchmarkData } from '@/hooks/useBenchmarkData';

interface ComparisonRow {
  metric: string;
  label: string;
  benchmark: number;
  store_value: number | null;
  difference_pct: number | null;
  status: string;
  lower_is_better: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  above: 'green',
  below: 'red',
  on_par: 'blue',
  no_data: 'default',
};

const STATUS_LABELS: Record<string, string> = {
  above: 'Above Average',
  below: 'Below Average',
  on_par: 'On Par',
  no_data: 'No Data',
};

const columns: ColumnsType<ComparisonRow> = [
  {
    title: 'Metric',
    dataIndex: 'label',
    key: 'label',
  },
  {
    title: 'Your Store',
    dataIndex: 'store_value',
    key: 'store_value',
    align: 'right',
    render: (val: number | null) => (val !== null ? val.toLocaleString() : '—'),
  },
  {
    title: 'Industry Avg.',
    dataIndex: 'benchmark',
    key: 'benchmark',
    align: 'right',
    render: (val: number) => val.toLocaleString(),
  },
  {
    title: 'Difference',
    dataIndex: 'difference_pct',
    key: 'difference_pct',
    align: 'right',
    render: (val: number | null, row: ComparisonRow) => {
      if (val === null) return '—';
      const isGood = row.lower_is_better ? val < 0 : val > 0;
      const color = isGood ? 'var(--novem-success)' : 'var(--novem-error)';
      return <span style={{ color, fontWeight: 500 }}>{val > 0 ? '+' : ''}{val}%</span>;
    },
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    align: 'center',
    render: (status: string, row: ComparisonRow) => {
      let color = STATUS_COLORS[status] ?? 'default';
      if (status === 'above' && row.lower_is_better) color = 'red';
      if (status === 'below' && row.lower_is_better) color = 'green';
      return <Tag color={color}>{STATUS_LABELS[status] ?? status}</Tag>;
    },
  },
];

export default function BenchmarkCard() {
  const { data, loading, error } = useBenchmarkData();

  if (loading) {
    return (
      <Card title="Industry Benchmarks">
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card title="Industry Benchmarks">
        <Empty description={error || 'No benchmark data available'} />
      </Card>
    );
  }

  return (
    <Card
      title="Industry Benchmarks"
      extra={<Tag>{data.industry.charAt(0).toUpperCase() + data.industry.slice(1)}</Tag>}
    >
      <Table
        columns={columns}
        dataSource={data.comparisons}
        rowKey="metric"
        pagination={false}
        size="small"
      />
    </Card>
  );
}
