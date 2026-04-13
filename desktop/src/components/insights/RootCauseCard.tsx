import { Card, Table, Tag, Empty } from 'antd';
import { ThunderboltOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

import type { RootCauseNarrative, DrillDown } from '@/types/insights';
import { formatCurrency } from '@/utils/formatCurrency';

import styles from './RootCauseCard.module.css';

interface Props {
  data: RootCauseNarrative | null;
}

const directionIcon = {
  up: <ArrowUpOutlined style={{ color: '#52c41a' }} />,
  down: <ArrowDownOutlined style={{ color: '#ff4d4f' }} />,
  flat: <MinusOutlined style={{ color: '#8c8c8c' }} />,
};

const drillColumns = [
  {
    title: 'Dimension',
    dataIndex: 'dimension',
    key: 'dimension',
    render: (v: string) => <Tag>{v}</Tag>,
  },
  {
    title: 'Top Contributor',
    dataIndex: 'top_contributor',
    key: 'top_contributor',
  },
  {
    title: 'Impact',
    dataIndex: 'impact',
    key: 'impact',
    render: (v: number | null) =>
      v != null ? (
        <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
          {v >= 0 ? '+' : ''}{formatCurrency(v)}
        </span>
      ) : '—',
  },
  {
    title: 'Detail',
    dataIndex: 'detail',
    key: 'detail',
    ellipsis: true,
  },
];

export default function RootCauseCard({ data }: Props) {
  if (!data) {
    return (
      <Card title={<><ThunderboltOutlined /> Root Cause Analysis</>}>
        <Empty description="No root cause analysis available" />
      </Card>
    );
  }

  return (
    <Card title={<><ThunderboltOutlined /> Root Cause Analysis</>}>
      <p className={styles.verdict}>
        {directionIcon[data.direction]} {data.verdict}
        {data.generated_by === 'ollama' && <span className={styles.aiBadge}>AI Generated</span>}
      </p>

      <p className={styles.changeLine}>
        Revenue changed{' '}
        <strong style={{ color: data.change_amount >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {data.change_amount >= 0 ? '+' : ''}{formatCurrency(data.change_amount)}
        </strong>{' '}
        ({data.change_pct >= 0 ? '+' : ''}{data.change_pct.toFixed(1)}%) over {data.period}
      </p>

      {data.primary_cause && (
        <Card size="small" type="inner" title="Primary Cause" style={{ marginBottom: 16 }}>
          <strong>{data.primary_cause.dimension}</strong> &mdash; {data.primary_cause.contributor}
          <br />
          Impact: <strong>{formatCurrency(data.primary_cause.impact)}</strong> ({data.primary_cause.impact_pct.toFixed(1)}%)
          <br />
          <span style={{ color: '#8c8c8c' }}>{data.primary_cause.detail}</span>
        </Card>
      )}

      <div className={styles.drillTable}>
        <Table
          dataSource={data.drill_downs}
          columns={drillColumns}
          rowKey={(r: DrillDown) => r.dimension}
          size="small"
          pagination={false}
        />
      </div>
    </Card>
  );
}
