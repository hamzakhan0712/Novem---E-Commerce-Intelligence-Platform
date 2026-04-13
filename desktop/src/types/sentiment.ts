export type SentimentPeriod = '7d' | '14d' | '30d' | '90d' | '6m' | '12m';

export interface SentimentDistribution {
  positive: number;
  neutral: number;
  negative: number;
}

export interface SentimentStats {
  total_reviews: number;
  avg_score: number;
  avg_rating: number;
  positive: number;
  neutral: number;
  negative: number;
}

export interface SentimentSummary {
  current: SentimentStats;
  previous: SentimentStats;
  changes: {
    total_reviews: number;
    avg_score: number;
    avg_rating: number;
    positive: number;
  };
  distribution: SentimentDistribution;
}

export interface RatingBreakdown {
  rating: number;
  count: number;
  avg_sentiment: number;
}

export interface SentimentTrendPoint {
  date: string;
  count: number;
  avg_score: number;
  positive: number;
  negative: number;
}

export interface ReviewItem {
  review_id: string;
  product_id: string | null;
  rating: number | null;
  text: string | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  date: string;
}

export interface ProductSentiment {
  product_id: string;
  review_count: number;
  avg_sentiment: number;
  avg_rating: number;
}

export interface KeywordItem {
  word: string;
  count: number;
}

export interface SentimentKeywords {
  positive_keywords: KeywordItem[];
  negative_keywords: KeywordItem[];
}
