import { useState } from 'react';

import { Card, Slider, Button, Statistic, Row, Col, Table, Tag, Empty, Alert, Typography } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

import { formatCurrency, getCurrencySymbol } from '@/utils/formatCurrency';
import type { ScenarioResult } from '@/types/insights';

import styles from './ScenarioSimulator.module.css';

interface Props {
  scenario: ScenarioResult | null;
  loading: boolean;
  onRun: (adjustments: Record<string, number>) => void;
}

const LEVERS = [
  { key: 'price_change_pct', label: 'Price Change', min: -30, max: 30, step: 1, suffix: '%' },
  { key: 'order_volume_change_pct', label: 'Order Volume Change', min: -30, max: 30, step: 1, suffix: '%' },
  { key: 'new_customer_change_pct', label: 'New Customer Acquisition', min: -20, max: 50, step: 5, suffix: '%' },
  { key: 'discount_change_pct', label: 'Discount Spend Change', min: -50, max: 50, step: 5, suffix: '%' },
  { key: 'channel_count_change', label: 'New Channels', min: 0, max: 3, step: 1, suffix: '' },
];

function buildComparisonChart(baseline: Record<string, number>, projected: Record<string, number>) {
  const metrics = ['revenue', 'orders', 'customers', 'aov'];
  const labels = ['Revenue', 'Orders', 'Customers', 'Avg. Order Value'];

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Baseline', 'Projected'], textStyle: { color: '#aaa' } },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      { name: 'Baseline', type: 'bar', data: metrics.map((m) => baseline[m] ?? 0), itemStyle: { color: '#595959' } },
      { name: 'Projected', type: 'bar', data: metrics.map((m) => projected[m] ?? 0), itemStyle: { color: '#52c41a' } },
    ],
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
  };
}

const impactColumns = [
  { title: 'Lever', dataIndex: 'lever', key: 'lever' },
  { title: 'Adjustment', dataIndex: 'adjustment', key: 'adjustment' },
  {
    title: 'Revenue Impact',
    dataIndex: 'revenue_impact',
    key: 'revenue_impact',
    render: (v: number) => {
      const color = v >= 0 ? '#52c41a' : '#ff4d4f';
      return <span style={{ color, fontWeight: 600 }}>{formatCurrency(v)}</span>;
    },
  },
  { title: 'Detail', dataIndex: 'detail', key: 'detail', ellipsis: true },
];

export default function ScenarioSimulator({ scenario, loading, onRun }: Props) {
  const [adjustments, setAdjustments] = useState<Record<string, number>>({});

  const handleChange = (key: string, value: number) => {
    setAdjustments((prev) => ({ ...prev, [key]: value }));
  };

  const hasChanges = Object.values(adjustments).some((v) => v !== 0);

  const hasResults = scenario && scenario.impacts && scenario.impacts.length > 0;

  return (
    <div className={styles.layout}>
      {/* Left column — simulation results */}
      <div className={styles.resultsCol}>
        {hasResults ? (
          <>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small">
                  <Statistic title="Baseline Revenue" value={scenario.baseline.revenue} prefix={getCurrencySymbol()} precision={0} />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic title="Projected Revenue" value={scenario.projected.revenue} prefix={getCurrencySymbol()} precision={0} valueStyle={{ color: '#52c41a' }} />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="Total Impact"
                    value={scenario.total_impact}
                    prefix={getCurrencySymbol()}
                    precision={0}
                    valueStyle={{ color: scenario.total_impact >= 0 ? '#52c41a' : '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="Impact %"
                    value={scenario.impact_pct}
                    suffix="%"
                    precision={1}
                    valueStyle={{ color: scenario.impact_pct >= 0 ? '#52c41a' : '#ff4d4f' }}
                  />
                </Card>
              </Col>
            </Row>

            <Card title="Baseline vs. Projected" size="small">
              <ReactECharts option={buildComparisonChart(scenario.baseline, scenario.projected)} style={{ height: 300 }} />
            </Card>

            <Card title="Impact Breakdown" size="small">
              <Table
                dataSource={scenario.impacts}
                columns={impactColumns}
                rowKey="lever"
                size="small"
                pagination={false}
              />
            </Card>

            {scenario.assumptions && scenario.assumptions.length > 0 && (
              <Alert
                type="info"
                showIcon
                message="Assumptions"
                description={
                  <Typography.Paragraph style={{ margin: 0 }}>
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {scenario.assumptions.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </Typography.Paragraph>
                }
                style={{ marginTop: 12 }}
              />
            )}

            {scenario.disclaimer && (
              <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                {scenario.disclaimer}
              </Typography.Text>
            )}
          </>
        ) : (
          <Card className={styles.placeholder}>
            <Empty
              description={scenario?.message || 'Adjust the levers and run a simulation to see projected results here.'}
            />
          </Card>
        )}
      </div>

      {/* Right column — levers */}
      <div className={styles.leversCol}>
        <Card title="Adjust Business Levers" size="small">
          <div className={styles.sliderGrid}>
            {LEVERS.map((lever) => (
              <div key={lever.key} className={styles.sliderItem}>
                <div className={styles.sliderLabel}>
                  <span>{lever.label}</span>
                  <Tag>{adjustments[lever.key] ?? 0}{lever.suffix}</Tag>
                </div>
                <Slider
                  min={lever.min}
                  max={lever.max}
                  step={lever.step}
                  value={adjustments[lever.key] ?? 0}
                  onChange={(v) => handleChange(lever.key, v)}
                  marks={{ [lever.min]: `${lever.min}`, 0: '0', [lever.max]: `${lever.max}` }}
                />
              </div>
            ))}
          </div>

          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={loading}
            disabled={!hasChanges}
            onClick={() => onRun(adjustments)}
            block
            style={{ marginTop: 16 }}
          >
            Run Simulation
          </Button>
        </Card>
      </div>
    </div>
  );
}
