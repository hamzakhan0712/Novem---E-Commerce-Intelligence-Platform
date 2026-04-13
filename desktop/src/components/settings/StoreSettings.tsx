import { useEffect } from 'react';

import { Button, Tag, Empty, Select } from 'antd';
import {
  ShopOutlined, PlusOutlined, LinkOutlined,
  CalendarOutlined, CloudUploadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useStoreStore } from '@/stores/storeStore';
import { ROUTES } from '@/constants/routes';

import styles from './StoreSettings.module.css';

export default function StoreSettings() {
  const navigate = useNavigate();
  const stores = useStoreStore((s) => s.stores);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const fetchStores = useStoreStore((s) => s.fetchStores);
  const setActiveStore = useStoreStore((s) => s.setActiveStore);

  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  const activeStore = stores.find((s) => s.id === activeStoreId);
  const otherStores = stores.filter((s) => s.id !== activeStoreId);

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h3 className={styles.title}>Your Stores</h3>
        <div className={styles.headerActions}>
          <Select
            value={activeStoreId ?? undefined}
            onChange={(val) => setActiveStore(val)}
            style={{ width: 200 }}
            placeholder="Select active store"
            options={stores.map((s) => ({ value: s.id, label: s.name }))}
          />
          <Button
            icon={<PlusOutlined />}
            onClick={() => navigate(ROUTES.STORES)}
            size="small"
          >
            Add Store
          </Button>
        </div>
      </div>

      {stores.length === 0 ? (
        <Empty description="No stores yet" />
      ) : (
        <div className={styles.storeList}>
          {activeStore && (
            <div className={styles.storeRow + ' ' + styles.storeRowActive}>
              <div className={styles.rowMain}>
                <div className={styles.rowIcon + ' ' + styles.rowIconActive}>
                  <ShopOutlined />
                </div>
                <div className={styles.rowInfo}>
                  <div className={styles.rowNameLine}>
                    <span className={styles.rowName}>{activeStore.name}</span>
                    <Tag color="green" className={styles.activeTag}>Active</Tag>
                    <Tag className={styles.platformTag}>{activeStore.platform}</Tag>
                  </div>
                  <div className={styles.rowMeta}>
                    <span>{activeStore.currency}</span>
                    {activeStore.industry && <span>· {activeStore.industry}</span>}
                    {activeStore.timezone && <span>· {activeStore.timezone}</span>}
                    {activeStore.url && (
                      <span className={styles.rowUrl}>· <LinkOutlined /> {activeStore.url}</span>
                    )}
                  </div>
                  {activeStore.description && (
                    <p className={styles.rowDesc}>{activeStore.description}</p>
                  )}
                </div>
                <Button size="small" onClick={() => navigate(ROUTES.STORES)}>Manage</Button>
              </div>

              {activeStore.data_summary && (
                <div className={styles.rowStats}>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>{(activeStore.data_summary.orders ?? 0).toLocaleString()}</span>
                    <span className={styles.statLabel}>Orders</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>{(activeStore.data_summary.customers ?? 0).toLocaleString()}</span>
                    <span className={styles.statLabel}>Customers</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>{(activeStore.data_summary.products ?? 0).toLocaleString()}</span>
                    <span className={styles.statLabel}>Products</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>{(activeStore.data_summary.reviews ?? 0).toLocaleString()}</span>
                    <span className={styles.statLabel}>Reviews</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>{(activeStore.data_summary.total_imports ?? 0).toLocaleString()}</span>
                    <span className={styles.statLabel}>Imports</span>
                  </div>
                </div>
              )}

              <div className={styles.rowDates}>
                <span className={styles.dateItem}>
                  <CalendarOutlined /> Created {new Date(activeStore.created_at).toLocaleDateString()}
                </span>
                {activeStore.data_summary?.last_import_at && (
                  <span className={styles.dateItem}>
                    <CloudUploadOutlined /> Last import {new Date(activeStore.data_summary.last_import_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          )}

          {otherStores.map((store) => (
            <div key={store.id} className={styles.storeRow}>
              <div className={styles.rowMain}>
                <div className={styles.rowIcon}>
                  <ShopOutlined />
                </div>
                <div className={styles.rowInfo}>
                  <div className={styles.rowNameLine}>
                    <span className={styles.rowName}>{store.name}</span>
                    <Tag className={styles.platformTag}>{store.platform}</Tag>
                  </div>
                  <span className={styles.rowMeta}>
                    {store.currency}{store.industry ? ` · ${store.industry}` : ''}
                  </span>
                </div>
                <div className={styles.rowActions}>
                  <Button size="small" onClick={() => setActiveStore(store.id)}>
                    Switch
                  </Button>
                  <Button size="small" onClick={() => navigate(ROUTES.STORES)}>
                    Edit
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
