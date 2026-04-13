import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

import { formatCurrency } from '@/utils/formatCurrency';
import type { MarketingKpiResponse } from '@/types/marketing';

import styles from './MarketingKpiCards.module.css';

interface MarketingKpiCardsProps {
  data: MarketingKpiResponse;
}

interface KpiDef {
  key: string;
  label: string;
  format: (v: number) => string;
  changeKey: string;
  invertColor?: boolean;
  tooltip: string;
}

const KPI_DEFS: KpiDef[] = [
  { key: 'total_spend', label: 'Total Spend', format: (v) => formatCurrency(v), changeKey: 'total_spend', tooltip: 'Total advertising expenditure across all channels' },
  { key: 'roas', label: 'ROAS', format: (v) => `${v.toFixed(2)}×`, changeKey: 'roas', tooltip: 'Return on ad spend — revenue generated per unit of currency spent' },
  { key: 'avg_cpc', label: 'Avg. CPC', format: (v) => formatCurrency(v), changeKey: 'avg_cpc', invertColor: true, tooltip: 'Average cost per click across campaigns' },
  { key: 'avg_ctr', label: 'CTR', format: (v) => `${v.toFixed(2)}%`, changeKey: 'avg_ctr', tooltip: 'Click-through rate — percentage of impressions that result in clicks' },
  { key: 'avg_cvr', label: 'CVR', format: (v) => `${v.toFixed(2)}%`, changeKey: 'avg_cvr', tooltip: 'Conversion rate — percentage of clicks that result in conversions' },
  { key: 'total_conversions', label: 'Conversions', format: (v) => v.toLocaleString('en-IN'), changeKey: 'total_conversions', tooltip: 'Total number of conversions from ad campaigns' },
];

export default function MarketingKpiCards({ data }: MarketingKpiCardsProps) {
  const { current, previous, changes } = data;

  return (
    <div className={styles.grid}>
      {KPI_DEFS.map((kpi) => {
        const value = (current as unknown as Record<string, number>)[kpi.key] ?? 0;
        const prevValue = (previous as unknown as Record<string, number>)[kpi.key] ?? 0;
        const change = (changes as unknown as Record<string, number>)[kpi.changeKey] ?? 0;
        const isUp = change > 0;
        const isDown = change < 0;

        return (
          <div key={kpi.key} className={styles.card}>
            <span className={styles.label}>
              {kpi.label}
              <Tooltip title={kpi.tooltip}>
                <InfoCircleOutlined className={styles.infoIcon} />
              </Tooltip>
            </span>
            <div className={styles.valueRow}>
              <span className={styles.value}>{kpi.format(value)}</span>
              <span
                className={`${styles.change} ${
                  isUp
                    ? kpi.invertColor ? styles.changeDown : styles.changeUp
                    : isDown
                      ? kpi.invertColor ? styles.changeUp : styles.changeDown
                      : styles.changeNeutral
                }`}
              >
                {isUp ? <ArrowUpOutlined /> : isDown ? <ArrowDownOutlined /> : <MinusOutlined />}
                {Math.abs(change)}%
              </span>
            </div>
            <span className={styles.prev}>vs. {kpi.format(prevValue)} previous period</span>
          </div>
        );
      })}
    </div>
  );
}
