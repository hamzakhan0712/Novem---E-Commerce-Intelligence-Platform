import { useState, useEffect, useMemo } from 'react';

import { Card, Statistic, Spin, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import type { ApiResponse } from '@/types/api';

import styles from './RetentionCurveCard.module.css';

interface CurvePoint {
  month: number;
  retention_pct: number;
  retained_count: number;
  total_cohort_size: number;
}

interface RetentionData {
  curve: CurvePoint[];
  summary: {
    month_0: number;
    month_1: number;
    month_3: number;
    month_6: number;
  };
}

export default function RetentionCurveCard() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const [data, setData] = useState<RetentionData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeStoreId) return;
    let cancelled = false;
    setLoading(true);
    apiClient
      .get<ApiResponse<RetentionData>>('/customers/retention/curves', {
        params: { store_id: activeStoreId },
      })
      .then((res) => {
        if (!cancelled && res.data.success) setData(res.data.data ?? null);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [activeStoreId]);

  const chartOption = useMemo(() => {
    if (!data || !data.curve.length) return null;
    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: Array<{ value: [number, number] }>) => {
          const p = params[0];
          return `Month ${p.value[0]}<br/>Retention: <strong>${p.value[1].toFixed(1)}%</strong>`;
        },
      },
      grid: { top: 20, right: 20, bottom: 40, left: 50 },
      xAxis: {
        type: 'value' as const,
        name: 'Months after first purchase',
        nameLocation: 'center' as const,
        nameGap: 28,
        min: 0,
        max: Math.max(...data.curve.map((c) => c.month)),
      },
      yAxis: {
        type: 'value' as const,
        name: 'Retention %',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' },
      },
      series: [
        {
          type: 'line',
          data: data.curve.map((c) => [c.month, c.retention_pct]),
          smooth: true,
          areaStyle: { opacity: 0.15 },
          lineStyle: { width: 2.5 },
          itemStyle: { color: '#1890ff' },
        },
      ],
    };
  }, [data]);

  if (loading) {
    return (
      <Card title="Retention Curve">
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      </Card>
    );
  }

  if (!data || !data.curve.length) {
    return (
      <Card title="Retention Curve">
        <Empty description="Not enough data for retention analysis" />
      </Card>
    );
  }

  return (
    <Card title="Retention Curve" className={styles.card}>
      <div className={styles.stats}>
        <Statistic title="Month 1" value={data.summary.month_1} suffix="%" precision={1} />
        <Statistic title="Month 3" value={data.summary.month_3} suffix="%" precision={1} />
        <Statistic title="Month 6" value={data.summary.month_6} suffix="%" precision={1} />
      </div>
      {chartOption && <ReactECharts option={chartOption} style={{ height: 260 }} />}
    </Card>
  );
}
