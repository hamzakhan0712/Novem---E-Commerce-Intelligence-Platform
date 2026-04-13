import { Table, Card, Tag, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';

import type { BasketAnalysis, BasketRule } from '@/types/products';

import styles from './BasketAnalysisPanel.module.css';

interface Props {
  data: BasketAnalysis | null;
}

const ruleColumns = [
  {
    title: 'If Bought',
    dataIndex: 'if_bought',
    key: 'if_bought',
    ellipsis: true,
  },
  {
    title: '→ Then Also Bought',
    dataIndex: 'then_also_bought',
    key: 'then_also_bought',
    ellipsis: true,
  },
  {
    title: 'Likelihood',
    dataIndex: 'confidence',
    key: 'confidence',
    render: (v: number) => `${(v * 100).toFixed(1)}%`,
    sorter: (a: BasketRule, b: BasketRule) => a.confidence - b.confidence,
    width: 110,
  },
  {
    title: 'Strength',
    dataIndex: 'lift',
    key: 'lift',
    render: (v: number) => {
      const color = v > 3 ? 'green' : v > 1.5 ? 'blue' : 'default';
      return <Tag color={color}>{v.toFixed(2)}×</Tag>;
    },
    sorter: (a: BasketRule, b: BasketRule) => a.lift - b.lift,
    defaultSortOrder: 'descend' as const,
    width: 100,
  },
  {
    title: 'Frequency',
    dataIndex: 'support',
    key: 'support',
    render: (v: number) => `${(v * 100).toFixed(2)}%`,
    width: 100,
  },
  {
    title: 'Orders',
    dataIndex: 'order_count',
    key: 'order_count',
    width: 80,
  },
];

function buildBubbleChart(rules: BasketRule[]) {
  const data = rules.slice(0, 30).map((r) => ([
    +(r.support * 100).toFixed(2),
    +(r.confidence * 100).toFixed(1),
    +r.lift.toFixed(2),
    `${r.if_bought} → ${r.then_also_bought}`,
  ]));

  return {
    tooltip: {
      formatter: (p: { value: [number, number, number, string] }) => {
        const [s, c, l, name] = p.value;
        return `<strong>${name}</strong><br/>Frequency: ${s}%<br/>Likelihood: ${c}%<br/>Strength: ${l}×`;
      },
    },
    xAxis: { name: 'Frequency %', nameLocation: 'middle', nameGap: 30 },
    yAxis: { name: 'Likelihood %', nameLocation: 'middle', nameGap: 40 },
    series: [{
      type: 'scatter',
      symbolSize: (val: number[]) => Math.min(Math.max(val[2] * 3, 6), 30),
      data,
      itemStyle: { color: '#52c41a', opacity: 0.7 },
    }],
    grid: { left: 60, right: 20, top: 20, bottom: 50 },
  };
}

export default function BasketAnalysisPanel({ data }: Props) {
  if (!data || (!data.rules.length && !data.frequent_pairs.length)) {
    return (
      <Card className={styles.panel}>
        <Empty description={data?.message || 'No co-purchase patterns found. More orders are needed to discover patterns.'} />
      </Card>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.metaRow}>
        <Tag color="blue">{data.model}</Tag>
        <span>{data.total_orders} orders analyzed</span>
        <span>{data.rules.length} rules found</span>
      </div>

      {data.rules.length > 0 && (
        <div className={styles.chartRow}>
          <Card title="Frequency vs Likelihood (bubble = strength)" size="small" className={styles.chart}>
            <ReactECharts option={buildBubbleChart(data.rules)} style={{ height: 280 }} />
          </Card>
        </div>
      )}

      <Card title="Co-Purchase Patterns" size="small">
        <Table
          dataSource={data.rules}
          columns={ruleColumns}
          rowKey={(r) => `${r.if_bought}_${r.then_also_bought}`}
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 700 }}
        />
      </Card>

      {data.frequent_pairs.length > 0 && (
        <Card title="Frequently Co-Purchased Pairs" size="small">
          <Table
            dataSource={data.frequent_pairs}
            columns={[
              { title: 'Products', dataIndex: 'products', key: 'products', render: (v: string[]) => v.join(' + ') },
              { title: 'Frequency', dataIndex: 'support', key: 'support', render: (v: number) => `${(v * 100).toFixed(2)}%`, width: 100 },
              { title: 'Orders', dataIndex: 'order_count', key: 'order_count', width: 80 },
            ]}
            rowKey={(r) => r.products.join('_')}
            size="small"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}
    </div>
  );
}
