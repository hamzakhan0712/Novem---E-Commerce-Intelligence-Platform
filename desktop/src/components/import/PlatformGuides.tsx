import { useState, useEffect } from 'react';

import { Collapse } from 'antd';
import {
  ShopOutlined,
  GlobalOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';

import type { PlatformGuide } from '@/types/ingestion';

import styles from './PlatformGuides.module.css';

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  shopify: <ShopOutlined />,
  amazon: <GlobalOutlined />,
  woocommerce: <GlobalOutlined />,
  flipkart: <GlobalOutlined />,
  generic: <QuestionCircleOutlined />,
};

export default function PlatformGuides() {
  const [expanded, setExpanded] = useState(false);
  const [guides, setGuides] = useState<PlatformGuide[]>([]);

  useEffect(() => {
    if (!expanded || guides.length > 0) return;
    apiClient
      .get<{ success: boolean; data: PlatformGuide[] }>('/ingestion/platform-guides')
      .then((res) => {
        if (res.data.success && res.data.data) setGuides(res.data.data);
      })
      .catch(() => { /* non-critical */ });
  }, [expanded, guides.length]);

  const collapseItems = guides.map((g) => ({
    key: g.platform,
    label: (
      <span className={styles.platformLabel}>
        {PLATFORM_ICONS[g.icon] ?? <GlobalOutlined />}
        <span>{g.platform}</span>
      </span>
    ),
    children: (
      <div className={styles.stepsContent}>
        {g.steps.split('\n').map((line, i) => (
          <p key={i} className={styles.stepLine}>
            {line.replace(/\*\*(.*?)\*\*/g, '$1')}
          </p>
        ))}
      </div>
    ),
  }));

  return (
    <div className={styles.container}>
      <button className={styles.toggle} onClick={() => setExpanded(!expanded)}>
        <GlobalOutlined className={styles.toggleIcon} />
        <span className={styles.toggleLabel}>Platform Export Guides</span>
        <span className={styles.toggleHint}>
          {expanded ? 'Hide' : 'Show'} how to export from Shopify, Amazon, WooCommerce, etc.
        </span>
        <span className={styles.chevron}>{expanded ? '▴' : '▾'}</span>
      </button>
      {expanded && guides.length > 0 && (
        <div className={styles.panel}>
          <Collapse
            ghost
            size="small"
            items={collapseItems}
          />
        </div>
      )}
    </div>
  );
}
