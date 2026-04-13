import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

import type { SentimentSummary } from '@/types/sentiment';

import styles from './SentimentStats.module.css';

interface Props {
  summary: SentimentSummary;
}

function ChangeIndicator({ value }: { value: number }) {
  const isUp = value > 0;
  const isDown = value < 0;
  const cls = isUp ? styles.changeUp : isDown ? styles.changeDown : styles.changeNeutral;

  return (
    <span className={`${styles.change} ${cls}`}>
      {isUp ? <ArrowUpOutlined /> : isDown ? <ArrowDownOutlined /> : <MinusOutlined />}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

export default function SentimentStats({ summary }: Props) {
  const { current, changes, distribution } = summary;
  const positiveRatio = current.total_reviews > 0
    ? ((distribution.positive / current.total_reviews) * 100).toFixed(0)
    : '0';

  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <span className={styles.label}>
          Total Reviews
          <Tooltip title="Number of customer reviews received in the selected period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{current.total_reviews.toLocaleString()}</span>
          <ChangeIndicator value={changes.total_reviews} />
        </div>
        <span className={styles.prev}>vs. {summary.previous.total_reviews.toLocaleString()} previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Avg. Rating
          <Tooltip title="Average star rating across all reviews in this period">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{current.avg_rating.toFixed(1)} ★</span>
          <ChangeIndicator value={changes.avg_rating} />
        </div>
        <span className={styles.prev}>vs. {summary.previous.avg_rating.toFixed(1)} ★ previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Sentiment Score
          <Tooltip title="Overall positivity score based on review text analysis (0–100%)">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{(current.avg_score * 100).toFixed(0)}%</span>
          <ChangeIndicator value={changes.avg_score} />
        </div>
        <span className={styles.prev}>vs. {(summary.previous.avg_score * 100).toFixed(0)}% previous period</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>
          Positive Ratio
          <Tooltip title="Percentage of reviews with a positive sentiment out of all reviews">
            <InfoCircleOutlined style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', cursor: 'help', marginLeft: 4 }} />
          </Tooltip>
        </span>
        <div className={styles.valueRow}>
          <span className={styles.value}>{positiveRatio}%</span>
          <ChangeIndicator value={changes.positive} />
        </div>
        <span className={styles.sub}>{distribution.positive} positive · {distribution.neutral} neutral · {distribution.negative} negative</span>
      </div>
    </div>
  );
}
