import { useState, useMemo } from 'react';

import { Table, Segmented, Input, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

import { formatCurrency } from '@/utils/formatCurrency';
import type { TopProduct, ProductSort } from '@/types/products';

import styles from './ProductTable.module.css';

interface Props {
  products: TopProduct[];
  loading: boolean;
  sortBy: ProductSort;
  onSortChange: (sort: ProductSort) => void;
}

function getPerformanceTag(product: TopProduct, allProducts: TopProduct[]) {
  if (allProducts.length === 0) return null;
  const maxRevenue = Math.max(...allProducts.map((p) => p.total_revenue));
  const ratio = product.total_revenue / maxRevenue;
  if (ratio >= 0.8) return <Tag color="gold">Top Seller</Tag>;
  if (ratio >= 0.5) return <Tag color="blue">Strong</Tag>;
  return null;
}

const SORT_OPTIONS = [
  { label: 'By Revenue', value: 'revenue' },
  { label: 'By Units', value: 'units' },
];

export default function ProductTable({ products, loading, sortBy, onSortChange }: Props) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return products;
    const term = search.toLowerCase();
    return products.filter(
      (p) =>
        p.product_name.toLowerCase().includes(term) ||
        (p.category && p.category.toLowerCase().includes(term))
    );
  }, [products, search]);

  const columns = [
    {
      title: 'Product',
      dataIndex: 'product_name',
      key: 'product_name',
      ellipsis: true,
      render: (name: string, record: TopProduct) => {
        const tag = getPerformanceTag(record, products);
        return (
          <span>
            {name} {tag}
          </span>
        );
      },
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (v: string | null) => v || '—',
      width: 140,
    },
    {
      title: 'Units Sold',
      dataIndex: 'total_units',
      key: 'total_units',
      sorter: (a: TopProduct, b: TopProduct) => a.total_units - b.total_units,
      width: 110,
    },
    {
      title: 'Revenue',
      dataIndex: 'total_revenue',
      key: 'total_revenue',
      render: (v: number) => formatCurrency(v),
      sorter: (a: TopProduct, b: TopProduct) => a.total_revenue - b.total_revenue,
      defaultSortOrder: 'descend' as const,
      width: 130,
    },
    {
      title: 'Avg. Price',
      dataIndex: 'avg_price',
      key: 'avg_price',
      render: (v: number) => formatCurrency(v),
      width: 120,
    },
    {
      title: 'Orders',
      dataIndex: 'order_count',
      key: 'order_count',
      width: 90,
    },
    {
      title: 'Buyers',
      dataIndex: 'unique_buyers',
      key: 'unique_buyers',
      width: 90,
    },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>
          Top Products <span className={styles.count}>({filtered.length})</span>
        </span>
        <div className={styles.controls}>
          <Input
            placeholder="Search products..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            allowClear
            size="small"
            className={styles.search}
          />
          <Segmented options={SORT_OPTIONS} value={sortBy} onChange={(v) => onSortChange(v as ProductSort)} size="small" />
        </div>
      </div>
      <Table
        dataSource={filtered}
        columns={columns}
        rowKey="product_id"
        loading={loading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (total) => `${total} products` }}
        scroll={{ x: 800 }}
      />
    </div>
  );
}
