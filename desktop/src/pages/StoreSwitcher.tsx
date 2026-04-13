import { useEffect } from 'react';

import { Button, Spin } from 'antd';
import { ShopOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useStoreStore } from '@/stores/storeStore';
import TitleBar from '@/components/shell/TitleBar';
import { ROUTES } from '@/constants/routes';

import styles from './StoreSwitcher.module.css';

export default function StoreSwitcher() {
  const navigate = useNavigate();
  const stores = useStoreStore((s) => s.stores);
  const loading = useStoreStore((s) => s.loading);
  const fetchStores = useStoreStore((s) => s.fetchStores);
  const setActiveStore = useStoreStore((s) => s.setActiveStore);

  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  const handleSelectStore = (storeId: string) => {
    setActiveStore(storeId);
    navigate(ROUTES.DASHBOARD);
  };

  if (loading && stores.length === 0) {
    return (
      <div className={styles.page}>
        <TitleBar minimal />
        <div className={styles.body}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <TitleBar minimal />
      <div className={styles.body}>
        <div className={styles.heading}>
          <h1 className={styles.title}>Select a Store</h1>
          <p className={styles.subtitle}>Choose a store to open, or create a new one</p>
        </div>

        <div className={styles.grid}>
          {stores.map((store) => {
            const counts = store.data_summary;
            return (
              <div
                key={store.id}
                className={styles.storeCard}
                onClick={() => handleSelectStore(store.id)}
              >
                <div className={styles.cardTop}>
                  <div className={styles.cardIcon}>
                    <ShopOutlined />
                  </div>
                  <div className={styles.cardInfo}>
                    <span className={styles.storeName}>{store.name}</span>
                    <span className={styles.storeMeta}>
                      {store.platform} · {store.currency}{store.industry ? ` · ${store.industry}` : ''}
                    </span>
                  </div>
                </div>
                {counts && (
                  <div className={styles.dataCounts}>
                    <div className={styles.countItem}>
                      <span className={styles.countValue}>{(counts.orders ?? 0).toLocaleString()}</span>
                      <span className={styles.countLabel}>Orders</span>
                    </div>
                    <div className={styles.countItem}>
                      <span className={styles.countValue}>{(counts.customers ?? 0).toLocaleString()}</span>
                      <span className={styles.countLabel}>Customers</span>
                    </div>
                    <div className={styles.countItem}>
                      <span className={styles.countValue}>{(counts.products ?? 0).toLocaleString()}</span>
                      <span className={styles.countLabel}>Products</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          <div className={styles.createCard} onClick={() => navigate(ROUTES.STORES)}>
            <PlusOutlined />
            Create New Store
          </div>
        </div>

        <div className={styles.footer}>
          <Button type="link" icon={<SettingOutlined />} onClick={() => navigate(ROUTES.STORES)}>
            Manage Stores
          </Button>
        </div>
      </div>
    </div>
  );
}
