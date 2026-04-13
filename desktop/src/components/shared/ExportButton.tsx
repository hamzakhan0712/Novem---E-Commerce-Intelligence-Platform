import { useState } from 'react';
import { Button, Dropdown, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

const EXPORT_TYPES = [
  { key: 'orders', label: 'Orders' },
  { key: 'customers', label: 'Customers' },
  { key: 'products', label: 'Products' },
];

export default function ExportButton() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const [loading, setLoading] = useState(false);

  const handleExport = async (dataType: string) => {
    if (!activeStoreId) {
      message.warning('Select a store first');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post(
        '/export/csv',
        {
          store_id: activeStoreId,
          data_type: dataType,
          format: 'csv',
        },
        { responseType: 'blob' },
      );

      const rowCount = res.headers['x-row-count'] ?? '0';
      const blob = new Blob([res.data as BlobPart], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${dataType}_export.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success(`Exported ${rowCount} ${dataType} rows`);
    } catch {
      message.error(`Failed to export ${dataType}`);
    } finally {
      setLoading(false);
    }
  };

  const menuItems: MenuProps['items'] = EXPORT_TYPES.map((t) => ({
    key: t.key,
    label: t.label,
    onClick: () => handleExport(t.key),
  }));

  return (
    <Dropdown menu={{ items: menuItems }} trigger={['click']} disabled={!activeStoreId}>
      <Button icon={<DownloadOutlined />} loading={loading}>
        Export
      </Button>
    </Dropdown>
  );
}
