import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import type { ReviewItem } from '@/types/sentiment';

import styles from './ReviewTable.module.css';

interface Props {
  reviews: ReviewItem[];
}

function sentimentColor(label: string | null): string {
  if (label === 'positive') return 'green';
  if (label === 'negative') return 'red';
  return 'orange';
}

function sentimentText(label: string | null): string {
  if (label === 'positive') return 'Positive';
  if (label === 'negative') return 'Negative';
  return 'Neutral';
}

export default function ReviewTable({ reviews }: Props) {
  const columns: ColumnsType<ReviewItem> = [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      width: 110,
      sorter: (a, b) => a.date.localeCompare(b.date),
      defaultSortOrder: 'descend',
      render: (v: string) => v?.slice(0, 10) ?? '—',
    },
    {
      title: 'Rating',
      dataIndex: 'rating',
      key: 'rating',
      width: 85,
      align: 'center',
      sorter: (a, b) => (a.rating ?? 0) - (b.rating ?? 0),
      render: (v: number | null) => (v != null ? `${v}★` : '—'),
    },
    {
      title: 'Review Text',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      render: (v: string | null) => (
        <span className={styles.reviewText}>{v || '(No text)'}</span>
      ),
    },
    {
      title: 'Score',
      dataIndex: 'sentiment_score',
      key: 'score',
      width: 80,
      align: 'center',
      sorter: (a, b) => (a.sentiment_score ?? 0) - (b.sentiment_score ?? 0),
      render: (v: number | null) => (v != null ? `${(v * 100).toFixed(0)}%` : '—'),
    },
    {
      title: 'Sentiment',
      dataIndex: 'sentiment_label',
      key: 'sentiment',
      width: 110,
      filters: [
        { text: 'Positive', value: 'positive' },
        { text: 'Neutral', value: 'neutral' },
        { text: 'Negative', value: 'negative' },
      ],
      onFilter: (value, record) => record.sentiment_label === value,
      render: (v: string | null) => (
        <Tag color={sentimentColor(v)}>{sentimentText(v)}</Tag>
      ),
    },
    {
      title: 'Product',
      dataIndex: 'product_id',
      key: 'product',
      width: 120,
      ellipsis: true,
      render: (v: string | null) => v || '—',
    },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>Recent Reviews</span>
        <Tag>{reviews.length} reviews</Tag>
      </div>
      <Table
        dataSource={reviews}
        columns={columns}
        rowKey="review_id"
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50'] }}
        scroll={{ y: 400 }}
      />
    </div>
  );
}
