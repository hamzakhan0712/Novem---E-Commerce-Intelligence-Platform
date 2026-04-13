import { Card, Table, Tag, Empty, Collapse } from 'antd';
import ReactECharts from 'echarts-for-react';

import type { ShapExplanation, ShapCustomerExplanation, ShapDriver } from '@/types/insights';

import styles from './ShapExplainPanel.module.css';

interface Props {
  data: ShapExplanation | null;
}

function buildImportanceChart(features: { feature: string; importance: number; label: string }[]) {
  const top10 = features.slice(0, 10);
  const labels = top10.map((f) => f.label).reverse();
  const values = top10.map((f) => f.importance).reverse();

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', name: 'Impact Score' },
    yAxis: { type: 'category', data: labels },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: (params: { dataIndex: number }) => {
          const colors = ['#52c41a', '#73d13d', '#95de64', '#b7eb8f', '#d9f7be', '#ffe58f', '#ffd666', '#ffc53d', '#faad14', '#fa8c16'];
          return colors[params.dataIndex] || '#52c41a';
        },
      },
    }],
    grid: { left: 160, right: 30, top: 10, bottom: 30 },
  };
}

function directionTag(d: ShapDriver) {
  if (d.direction === 'increases_churn') {
    return <Tag color="red">↑ Inactivity Risk</Tag>;
  }
  return <Tag color="green">↓ Inactivity Risk</Tag>;
}

export default function ShapExplainPanel({ data }: Props) {
  if (!data || data.model === 'insufficient_data' || data.model === 'insufficient_variance') {
    return (
      <Card className={styles.panel}>
        <Empty description={data?.message || 'Need more data to analyze what drives customer behavior.'} />
      </Card>
    );
  }

  const collapseItems = data.sample_explanations.map((exp: ShapCustomerExplanation) => ({
    key: exp.customer_id,
    label: (
      <div className={styles.collapseLabel}>
        <span>{exp.customer_id}</span>
        <Tag color={exp.churn_probability > 0.7 ? 'red' : exp.churn_probability > 0.4 ? 'orange' : 'green'}>
          {(exp.churn_probability * 100).toFixed(1)}% inactivity risk
        </Tag>
      </div>
    ),
    children: (
      <Table
        dataSource={exp.top_drivers}
        columns={[
          { title: 'Feature', dataIndex: 'label', key: 'label' },
          { title: 'Value', dataIndex: 'feature_value', key: 'feature_value', width: 100 },
          { title: 'Impact Score', dataIndex: 'shap_value', key: 'shap_value', render: (v: number) => v.toFixed(4), width: 120 },
          { title: 'Direction', key: 'direction', render: (_: unknown, r: ShapDriver) => directionTag(r), width: 130 },
        ]}
        rowKey="feature"
        size="small"
        pagination={false}
      />
    ),
  }));

  return (
    <div className={styles.panel}>
      <div className={styles.metaRow}>
        <Tag color="purple">{data.model}</Tag>
        <span>Accuracy: <strong>{(data.summary.model_accuracy * 100).toFixed(1)}%</strong></span>
        <span>{data.summary.total_customers} customers analyzed</span>
        <span>{data.summary.churned_count ?? 0} inactive / {data.summary.active_count ?? 0} active</span>
      </div>

      <Card title="What Drives Customer Behavior" size="small">
        <ReactECharts option={buildImportanceChart(data.global_importance)} style={{ height: 320 }} />
      </Card>

      {data.sample_explanations.length > 0 && (
        <Card title="Individual Customer Breakdown (Top 10 Highest Risk)" size="small">
          <Collapse items={collapseItems} defaultActiveKey={[data.sample_explanations[0]?.customer_id]} />
        </Card>
      )}
    </div>
  );
}
