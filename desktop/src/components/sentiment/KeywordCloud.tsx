import { Tag, Empty } from 'antd';

import type { SentimentKeywords as KeywordsData } from '@/types/sentiment';

import styles from './KeywordCloud.module.css';

interface Props {
  keywords: KeywordsData;
}

export default function KeywordCloud({ keywords }: Props) {
  const hasPositive = keywords.positive_keywords.length > 0;
  const hasNegative = keywords.negative_keywords.length > 0;

  if (!hasPositive && !hasNegative) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Top Keywords</div>
        <div className={styles.emptyWrap}>
          <Empty description="No keyword data for this period" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const maxCount = Math.max(
    ...keywords.positive_keywords.map((k) => k.count),
    ...keywords.negative_keywords.map((k) => k.count),
    1,
  );

  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>Top Keywords</div>
      <div className={styles.columns}>
        <div className={styles.col}>
          <span className={styles.colLabel}>
            <span className={styles.dotPositive} /> Positive Reviews
          </span>
          <div className={styles.tagCloud}>
            {keywords.positive_keywords.map((k) => {
              const scale = 0.7 + (k.count / maxCount) * 0.6;
              return (
                <Tag
                  key={k.word}
                  color="green"
                  style={{ fontSize: `${scale}em`, margin: '2px 4px' }}
                >
                  {k.word} ({k.count})
                </Tag>
              );
            })}
            {!hasPositive && <span className={styles.noData}>No keywords</span>}
          </div>
        </div>
        <div className={styles.col}>
          <span className={styles.colLabel}>
            <span className={styles.dotNegative} /> Negative Reviews
          </span>
          <div className={styles.tagCloud}>
            {keywords.negative_keywords.map((k) => {
              const scale = 0.7 + (k.count / maxCount) * 0.6;
              return (
                <Tag
                  key={k.word}
                  color="red"
                  style={{ fontSize: `${scale}em`, margin: '2px 4px' }}
                >
                  {k.word} ({k.count})
                </Tag>
              );
            })}
            {!hasNegative && <span className={styles.noData}>No keywords</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
