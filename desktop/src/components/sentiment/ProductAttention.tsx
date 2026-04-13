import { Table, Tag, Empty } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import type { ProductSentiment } from '@/types/sentiment';

import styles from './ProductAttention.module.css';

interface Props {
  products: ProductSentiment[];
}

export default function ProductAttention({ products }: Props) {
  if (products.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.title}>Products Needing Attention</div>
        <div className={styles.emptyWrap}>
          <Empty description="No product sentiment data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      </div>
    );
  }

  const columns: ColumnsType<ProductSentiment> = [
    {
      title: 'Product',
      dataIndex: 'product_id',
      key: 'product_id',
      ellipsis: true,
    },
    {
      title: 'Reviews',
      dataIndex: 'review_count',
      key: 'reviews',
      width: 90,
      align: 'center',
      sorter: (a, b) => a.review_count - b.review_count,
    },
    {
      title: 'Avg Rating',
      dataIndex: 'avg_rating',
      key: 'rating',
      width: 110,
      align: 'center',
      sorter: (a, b) => a.avg_rating - b.avg_rating,
      render: (v: number) => `${v.toFixed(1)} ★`,
    },
    {
      title: 'Sentiment',
      dataIndex: 'avg_sentiment',
      key: 'sentiment',
      width: 120,
      align: 'center',
      sorter: (a, b) => a.avg_sentiment - b.avg_sentiment,
      defaultSortOrder: 'ascend',
      render: (v: number) => {
        const pct = (v * 100).toFixed(0);
        const color = v <= 0.4 ? 'red' : v >= 0.6 ? 'green' : 'orange';
        return <Tag color={color}>{pct}%</Tag>;
      },
    },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>Products Needing Attention</span>
        <Tag color="red">{products.length} flagged</Tag>
      </div>
      <Table
        dataSource={products}
        columns={columns}
        rowKey="product_id"
        size="small"
        pagination={false}
        scroll={{ y: 300 }}
      />
    </div>
  );
}
