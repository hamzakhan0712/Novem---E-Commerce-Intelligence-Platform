import { useState, useCallback, useMemo, useRef, useEffect } from 'react';

import { Card, Slider, Statistic, Empty } from 'antd';
import { HistoryOutlined, PlayCircleOutlined, PauseCircleOutlined, UndoOutlined } from '@ant-design/icons';
import { Button, Tooltip } from 'antd';
import ReactECharts from 'echarts-for-react';

import type { CohortReplay } from '@/types/customers';

import styles from './CohortReplayPanel.module.css';

interface Props {
  data: CohortReplay | null;
  onReplayChange?: (month: string) => void;
}

function buildHeatmapOption(data: CohortReplay) {
  const cohorts = data.cohorts;
  const yLabels = cohorts.map((c) => c.cohort_month);
  const maxMonthIdx = Math.max(0, ...cohorts.flatMap((c) => c.months.map((m) => m.month_index)));
  const xLabels = Array.from({ length: maxMonthIdx + 1 }, (_, i) => `M${i}`);

  const heatData: [number, number, number][] = [];
  cohorts.forEach((c, yi) => {
    c.months.forEach((m) => {
      heatData.push([m.month_index, yi, Math.round(m.retention_pct * 100) / 100]);
    });
  });

  return {
    tooltip: {
      formatter: (params: { value: [number, number, number] }) => {
        const [mi, ci, pct] = params.value;
        return `${yLabels[ci]} &rarr; Month ${mi}<br/>Return Rate: <strong>${pct.toFixed(1)}%</strong>`;
      },
    },
    grid: { top: 30, right: 30, bottom: 50, left: 90 },
    xAxis: { type: 'category' as const, data: xLabels, splitArea: { show: true } },
    yAxis: { type: 'category' as const, data: yLabels, splitArea: { show: true } },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f5f5f5', '#bae7ff', '#1890ff', '#003a8c'] },
    },
    series: [
      {
        type: 'heatmap',
        data: heatData,
        label: {
          show: heatData.length < 120,
          formatter: (params: { value: [number, number, number] }) => `${params.value[2].toFixed(0)}%`,
          fontSize: 10,
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
      },
    ],
  };
}

export default function CohortReplayPanel({ data, onReplayChange }: Props) {
  const [sliderIdx, setSliderIdx] = useState<number>(0);
  const [playing, setPlaying] = useState(false);
  const [initialData, setInitialData] = useState<CohortReplay | null>(null);
  const [isReplaying, setIsReplaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Capture the initial data snapshot on first load or when a full reset happens
  useEffect(() => {
    if (data && !isReplaying) {
      setInitialData(data);
      setSliderIdx(0);
    }
  }, [data, isReplaying]);

  const activeData = isReplaying ? data : initialData;
  const months = initialData?.available_months ?? [];

  const debouncedReplay = useCallback(
    (idx: number) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        if (months[idx] && onReplayChange) {
          setIsReplaying(true);
          onReplayChange(months[idx]);
        }
      }, 150);
    },
    [months, onReplayChange],
  );

  const handleSlider = useCallback(
    (val: number) => {
      setSliderIdx(val);
      debouncedReplay(val);
    },
    [debouncedReplay],
  );

  const handleReset = useCallback(() => {
    setPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);
    setSliderIdx(0);
    setIsReplaying(false);
    // Re-fetch without a replay month to restore original data
    if (onReplayChange) onReplayChange('');
  }, [onReplayChange]);

  const togglePlay = useCallback(() => {
    setPlaying((prev) => !prev);
  }, []);

  useEffect(() => {
    if (playing && months.length > 1) {
      timerRef.current = setInterval(() => {
        setSliderIdx((prev) => {
          const next = prev >= months.length - 1 ? 0 : prev + 1;
          if (months[next] && onReplayChange) {
            setIsReplaying(true);
            onReplayChange(months[next]);
          }
          if (next === 0 && prev === months.length - 1) {
            setPlaying(false);
            setIsReplaying(false);
          }
          return next;
        });
      }, 800);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [playing, months, onReplayChange]);

  const heatmapOption = useMemo(() => {
    if (!activeData || !activeData.cohorts.length) return null;
    return buildHeatmapOption(activeData);
  }, [activeData]);

  const summaryText = useMemo(() => {
    if (!activeData) return null;
    const { total_cohorts, total_customers, avg_month1_retention } = activeData.summary;
    const cohorts = activeData.cohorts;
    if (!cohorts.length) return null;

    const lines: string[] = [];

    if (avg_month1_retention != null) {
      const retPct = avg_month1_retention.toFixed(1);
      if (avg_month1_retention >= 30) {
        lines.push(`Strong early retention — ${retPct}% of customers return within the first month, indicating good product-market fit.`);
      } else if (avg_month1_retention >= 15) {
        lines.push(`Moderate early retention — ${retPct}% of customers come back after their first purchase. Consider loyalty nudges to boost this.`);
      } else {
        lines.push(`Low early retention — only ${retPct}% of customers return in month 1. Focus on post-purchase engagement (e.g., follow-up emails, discounts).`);
      }
    }

    lines.push(`Tracking ${total_customers.toLocaleString()} customers across ${total_cohorts} monthly groups.`);

    // Check for improvement trend
    if (cohorts.length >= 3) {
      const recent = cohorts.slice(-3);
      const recentM1 = recent
        .map((c) => c.months.find((m) => m.month_index === 1))
        .filter(Boolean);
      if (recentM1.length >= 2) {
        const first = recentM1[0]!.retention_pct;
        const last = recentM1[recentM1.length - 1]!.retention_pct;
        if (last > first + 2) {
          lines.push('Recent cohorts show improving return rates — your retention efforts are paying off.');
        } else if (last < first - 2) {
          lines.push('Recent cohorts show declining return rates — investigate whether product quality or service issues may be contributing.');
        }
      }
    }

    return lines;
  }, [activeData]);

  if (!activeData || !activeData.cohorts.length) {
    return (
      <Card title={<><HistoryOutlined /> Repeat Purchase Timeline</>}>
        <Empty description="No repeat purchase data available" />
      </Card>
    );
  }

  const marks: Record<number, string> = {};
  if (months.length > 0) {
    marks[0] = months[0];
    marks[months.length - 1] = months[months.length - 1];
  }

  return (
    <div>
      {months.length > 1 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <div className={styles.sliderWrap}>
            <Tooltip title={playing ? 'Pause replay' : 'Auto-play through months'}>
              <Button
                type="text"
                size="small"
                icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={togglePlay}
                className={styles.playBtn}
              />
            </Tooltip>
            <span className={styles.sliderLabel}>
              Time Travel: <strong>{months[sliderIdx] ?? '—'}</strong>
            </span>
            <Slider
              min={0}
              max={months.length - 1}
              value={sliderIdx}
              onChange={handleSlider}
              marks={marks}
              tooltip={{ formatter: (val) => (val != null ? months[val] ?? '' : '') }}
              className={styles.slider}
            />
            {isReplaying && (
              <Tooltip title="Reset to original view">
                <Button
                  type="text"
                  size="small"
                  icon={<UndoOutlined />}
                  onClick={handleReset}
                  className={styles.resetBtn}
                />
              </Tooltip>
            )}
          </div>
        </Card>
      )}

      <div className={styles.summaryRow}>
        <Card className={styles.summaryCard} size="small">
          <Statistic title="Customer Groups" value={activeData.summary.total_cohorts} />
        </Card>
        <Card className={styles.summaryCard} size="small">
          <Statistic title="Total Customers" value={activeData.summary.total_customers} />
        </Card>
        {activeData.summary.avg_month1_retention != null && (
          <Card className={styles.summaryCard} size="small">
            <Statistic
              title="Month 1 Return Rate"
              value={activeData.summary.avg_month1_retention}
              precision={1}
              suffix="%"
            />
          </Card>
        )}
      </div>

      <Card title="Return Rate Heatmap" className={styles.heatmapWrap} size="small">
        {heatmapOption && <ReactECharts option={heatmapOption} style={{ height: 360 }} notMerge />}
      </Card>

      {summaryText && summaryText.length > 0 && (
        <div className={styles.insight}>
          <div className={styles.insightTitle}>Key Takeaway</div>
          {summaryText.map((line, i) => (
            <p key={i} className={styles.insightLine}>{line}</p>
          ))}
        </div>
      )}
    </div>
  );
}
