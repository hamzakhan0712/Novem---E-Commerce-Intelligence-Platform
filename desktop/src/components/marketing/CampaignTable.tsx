import { useState } from 'react';

import { Table, Tag, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { formatCurrency } from '@/utils/formatCurrency';
import type { CampaignPerformance, CampaignSortField } from '@/types/marketing';

import styles from './CampaignTable.module.css';

interface CampaignTableProps {
  data: CampaignPerformance[];
  sortBy: CampaignSortField;
  onSortChange: (sort: CampaignSortField) => void;
}

const CHANNEL_COLORS: Record<string, string> = {
  google_ads: 'blue',
  meta_ads: 'geekblue',
  tiktok: 'default',
  email: 'gold',
  affiliate: 'purple',
};

const CHANNEL_LABELS: Record<string, string> = {
  google_ads: 'Google Ads',
  meta_ads: 'Meta Ads',
  tiktok: 'TikTok',
  email: 'Email',
  affiliate: 'Affiliate',
};

const SORT_OPTIONS = [
  { label: 'ROAS', value: 'roas' },
  { label: 'Spend', value: 'spend' },
  { label: 'Revenue', value: 'revenue' },
  { label: 'Conversions', value: 'conversions' },
  { label: 'CPC', value: 'cpc' },
  { label: 'CTR', value: 'ctr' },
];

export default function CampaignTable({ data, sortBy, onSortChange }: CampaignTableProps) {
  const [channelFilter, setChannelFilter] = useState<string | null>(null);

  const filtered = channelFilter ? data.filter((c) => c.channel === channelFilter) : data;
  const channelOptions = [...new Set(data.map((c) => c.channel))].map((ch) => ({
    label: CHANNEL_LABELS[ch] || ch,
    value: ch,
  }));

  const columns: ColumnsType<CampaignPerformance> = [
    {
      title: 'Channel',
      dataIndex: 'channel',
      width: 120,
      render: (ch: string) => <Tag color={CHANNEL_COLORS[ch] || 'default'}>{CHANNEL_LABELS[ch] || ch}</Tag>,
    },
    { title: 'Campaign', dataIndex: 'campaign_name', ellipsis: true },
    {
      title: 'Spend',
      dataIndex: 'spend',
      width: 110,
      align: 'right',
      render: (v: number) => formatCurrency(v),
      sorter: (a, b) => a.spend - b.spend,
    },
    {
      title: 'Revenue',
      dataIndex: 'revenue',
      width: 110,
      align: 'right',
      render: (v: number) => formatCurrency(v),
      sorter: (a, b) => a.revenue - b.revenue,
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      width: 80,
      align: 'right',
      render: (v: number) => <span style={{ color: v >= 1 ? 'var(--novem-success)' : 'var(--novem-error)' }}>{v.toFixed(2)}×</span>,
      sorter: (a, b) => a.roas - b.roas,
    },
    {
      title: 'CPC',
      dataIndex: 'cpc',
      width: 80,
      align: 'right',
      render: (v: number) => formatCurrency(v),
      sorter: (a, b) => a.cpc - b.cpc,
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      width: 70,
      align: 'right',
      render: (v: number) => `${v.toFixed(2)}%`,
      sorter: (a, b) => a.ctr - b.ctr,
    },
    {
      title: 'CVR',
      dataIndex: 'cvr',
      width: 70,
      align: 'right',
      render: (v: number) => `${v.toFixed(2)}%`,
      sorter: (a, b) => a.cvr - b.cvr,
    },
    {
      title: 'Conv.',
      dataIndex: 'conversions',
      width: 80,
      align: 'right',
      render: (v: number) => v.toLocaleString('en-IN'),
      sorter: (a, b) => a.conversions - b.conversions,
    },
    {
      title: 'Days',
      dataIndex: 'active_days',
      width: 60,
      align: 'right',
    },
  ];

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>Campaign Performance</h3>
        <div className={styles.controls}>
          <Select
            size="small"
            placeholder="All channels"
            allowClear
            options={channelOptions}
            value={channelFilter}
            onChange={setChannelFilter}
            style={{ width: 140 }}
          />
          <Select
            size="small"
            options={SORT_OPTIONS}
            value={sortBy}
            onChange={onSortChange}
            style={{ width: 120 }}
          />
        </div>
      </div>
      <Table
        rowKey={(r) => `${r.channel}-${r.campaign_name}`}
        columns={columns}
        dataSource={filtered}
        size="small"
        pagination={{ pageSize: 15, showSizeChanger: false }}
        scroll={{ x: 900 }}
      />
    </div>
  );
}
