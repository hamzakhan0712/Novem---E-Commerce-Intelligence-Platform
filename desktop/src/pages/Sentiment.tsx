import { Segmented, Alert, Button } from 'antd';

import { useSentimentData } from '@/hooks/useSentimentData';
import { useSentimentStore } from '@/stores/sentimentStore';
import { DataGate } from '@/components/shared';
import {
  SentimentStats,
  SentimentDistribution,
  SentimentTrend,
  RatingBreakdown,
  ReviewTable,
  ProductAttention,
  KeywordCloud,
} from '@/components/sentiment';

import type { SentimentPeriod } from '@/types/sentiment';

import styles from './Sentiment.module.css';

const PERIOD_OPTIONS = [
  { value: '7d', label: '7 Days' },
  { value: '14d', label: '14 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '6m', label: '6 Months' },
  { value: '12m', label: '12 Months' },
];

export default function Sentiment() {
  const {
    summary, trend, ratings, reviews, products, keywords,
    error, analyzing, handleAnalyze,
  } = useSentimentData();
  const period = useSentimentStore((s) => s.period);
  const setPeriod = useSentimentStore((s) => s.setPeriod);

  return (
    <DataGate pageKey="sentiment" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Customer Reviews</h1>
          <span className={styles.subtitle}>Review insights and customer sentiment trends</span>
        </div>
        <div className={styles.headerRight}>
          <Segmented
            value={period}
            options={PERIOD_OPTIONS}
            onChange={(val) => setPeriod(val as SentimentPeriod)}
          />
          <Button loading={analyzing} onClick={handleAnalyze}>
            Analyze Unscored
          </Button>
        </div>
      </div>

      {error && (
        <Alert type="warning" showIcon closable message={error} />
      )}

      {summary && <SentimentStats summary={summary} />}

      <div className={styles.chartGrid}>
        {summary?.distribution && <SentimentDistribution distribution={summary.distribution} />}
        <RatingBreakdown data={ratings} />
      </div>

      <SentimentTrend data={trend} />

      <div className={styles.chartGrid}>
        {keywords && <KeywordCloud keywords={keywords} />}
        <ProductAttention products={products} />
      </div>

      <ReviewTable reviews={reviews} />
    </div>
    </DataGate>
  );
}
