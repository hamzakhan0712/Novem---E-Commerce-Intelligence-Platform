import { useState, useMemo } from 'react';
import { Table, Input, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

import type { TopCustomer } from '@/types/customers';

import { formatCurrency } from '@/utils/formatCurrency';

import styles from './CustomerTable.module.css';

interface Props {
  customers: TopCustomer[];
  loading: boolean;
}

function getSpendTag(spend: number, customers: TopCustomer[]): { color: string; label: string } {
  if (customers.length === 0) return { color: 'default', label: '' };
  const sorted = [...customers].sort((a, b) => a.total_spend - b.total_spend);
  const p75 = sorted[Math.floor(sorted.length * 0.75)]?.total_spend ?? 0;
  const p25 = sorted[Math.floor(sorted.length * 0.25)]?.total_spend ?? 0;
  if (spend >= p75) return { color: 'gold', label: 'VIP' };
  if (spend >= p25) return { color: 'blue', label: 'Regular' };
  return { color: 'default', label: 'Low' };
}

export default function CustomerTable({ customers, loading }: Props) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return customers;
    const q = search.toLowerCase();
    return customers.filter((c) => c.customer_id.toLowerCase().includes(q));
  }, [customers, search]);

  const columns = [
    {
      title: 'Customer',
      dataIndex: 'customer_id',
      key: 'customer_id',
      ellipsis: true,
    },
    {
      title: 'Tier',
      key: 'tier',
      width: 80,
      render: (_: unknown, record: TopCustomer) => {
        const tag = getSpendTag(record.total_spend, customers);
        return tag.label ? <Tag color={tag.color}>{tag.label}</Tag> : '—';
      },
    },
    {
      title: 'Orders',
      dataIndex: 'order_count',
      key: 'order_count',
      sorter: (a: TopCustomer, b: TopCustomer) => a.order_count - b.order_count,
      width: 90,
    },
    {
      title: 'Total Spend',
      dataIndex: 'total_spend',
      key: 'total_spend',
      render: (v: number) => formatCurrency(v),
      sorter: (a: TopCustomer, b: TopCustomer) => a.total_spend - b.total_spend,
      defaultSortOrder: 'descend' as const,
      width: 130,
    },
    {
      title: 'Avg. Order',
      dataIndex: 'avg_order_value',
      key: 'avg_order_value',
      render: (v: number) => formatCurrency(v),
      width: 120,
    },
    {
      title: 'First Order',
      dataIndex: 'first_order',
      key: 'first_order',
      render: (v: string | null) => v ? new Date(v).toLocaleDateString() : '—',
      width: 110,
    },
    {
      title: 'Last Order',
      dataIndex: 'last_order',
      key: 'last_order',
      render: (v: string | null) => v ? new Date(v).toLocaleDateString() : '—',
      width: 110,
    },
  ];

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.title}>Top Customers</span>
        <Input
          placeholder="Search customers..."
          prefix={<SearchOutlined />}
          allowClear
          className={styles.search}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <Table
        dataSource={filtered}
        columns={columns}
        rowKey="customer_id"
        loading={loading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (t) => `${t} customers` }}
        scroll={{ x: 760 }}
      />
    </div>
  );
}
