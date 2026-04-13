import { useState } from 'react';

import { Button, Select, Tooltip } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

import type { DataType } from '@/types/ingestion';

import styles from './TemplateDownload.module.css';

const ENGINE_BASE_URL = import.meta.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:44945';

const DATA_TYPE_OPTIONS: { value: DataType; label: string }[] = [
  { value: 'orders', label: 'Orders' },
  { value: 'customers', label: 'Customers' },
  { value: 'products', label: 'Products' },
  { value: 'ad_spend', label: 'Ad Spend' },
  { value: 'reviews', label: 'Reviews' },
  { value: 'stock_levels', label: 'Stock Levels' },
];

export default function TemplateDownload() {
  const [selectedType, setSelectedType] = useState<DataType>('orders');

  const handleDownload = () => {
    const url = `${ENGINE_BASE_URL}/ingestion/template/${selectedType}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `novem_template_${selectedType}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <DownloadOutlined className={styles.icon} />
        <div className={styles.headerText}>
          <span className={styles.title}>Download Template</span>
          <span className={styles.desc}>Get a ready-to-fill CSV with the correct column headers and example data</span>
        </div>
      </div>
      <div className={styles.actions}>
        <Select
          size="small"
          value={selectedType}
          onChange={setSelectedType}
          options={DATA_TYPE_OPTIONS}
          style={{ width: 140 }}
        />
        <Tooltip title={`Download ${selectedType} template CSV`}>
          <Button size="small" icon={<DownloadOutlined />} onClick={handleDownload}>
            Download CSV
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}
