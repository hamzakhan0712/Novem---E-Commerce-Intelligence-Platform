import { Card, Empty, Tag } from 'antd';
import { ExperimentOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

import type { BusinessDna } from '@/types/insights';

import styles from './BusinessDnaRadar.module.css';

interface Props {
  data: BusinessDna | null;
}

function buildRadarOption(data: BusinessDna) {
  const primaryColor = '#52c41a'; // single source of truth

  const indicator = data.dimensions.map((d) => ({
    name: d.label,
    max: 100,
  }));

  return {
    tooltip: {},
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      radius: '70%',
      axisName: {
        color: primaryColor, // match series color
        fontSize: 12,
        fontWeight: 600,
      },
      splitLine: { lineStyle: { color: 'var(--novem-border-strong)' } },
      splitArea: {
        areaStyle: {
          color: [
            'transparent',
            'rgba(82, 196, 26, 0.03)',
            'transparent',
            'rgba(82, 196, 26, 0.03)',
          ],
        },
      },
      axisLine: { lineStyle: { color: 'var(--novem-border-strong)' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: data.dimensions.map((d) => d.score),
            name: data.archetype,
            areaStyle: { opacity: 0.15, color: primaryColor },
            lineStyle: { color: primaryColor, width: 2 },
            itemStyle: { color: primaryColor },
          },
        ],
      },
    ],
  };
}

export default function BusinessDnaRadar({ data }: Props) {
  if (!data || !data.dimensions.length) {
    return (
      <Card title={<><ExperimentOutlined /> Store Profile</>}>
        <Empty description="Not enough data for store profiling" />
      </Card>
    );
  }

  const sorted = [...data.dimensions].sort((a, b) => b.score - a.score);
  const topDim = sorted[0];
  const weakDim = sorted[sorted.length - 1];

  return (
    <div className={styles.layout}>
      <Card className={styles.chartCard} title={<><ExperimentOutlined /> Store Profile Radar</>}>
        <ReactECharts option={buildRadarOption(data)} style={{ height: 520, width: '100%' }} />
      </Card>

      <div className={styles.sidebar}>
        <Card className={styles.archetypeCard} size="small">
          <Tag className={styles.archetypeBadge}>{data.archetype}</Tag>
          <p className={styles.summary}>{data.archetype_description}</p>
          <div className={styles.highlights}>
            <div className={styles.highlight}>
              <RiseOutlined className={styles.highlightIconUp} />
              <div>
                <div className={styles.highlightLabel}>Strongest</div>
                <div className={styles.highlightValue}>{topDim.label} — {Math.round(topDim.score)}</div>
              </div>
            </div>
            <div className={styles.highlight}>
              <FallOutlined className={styles.highlightIconDown} />
              <div>
                <div className={styles.highlightLabel}>Needs attention</div>
                <div className={styles.highlightValue}>{weakDim.label} — {Math.round(weakDim.score)}</div>
              </div>
            </div>
          </div>
        </Card>

        <div className={styles.dimList}>
          {sorted.map((d) => (
            <Card key={d.name} className={styles.dimCard} size="small">
              <div className={styles.dimCardInner}>
                <div className={styles.dimScore}>{Math.round(d.score)}</div>
                <div className={styles.dimInfo}>
                  <span className={styles.dimName}>{d.label}</span>
                  <div className={styles.dimBar}>
                    <div
                      className={styles.dimBarFill}
                      style={{ width: `${Math.round(d.score)}%` }}
                    />
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
