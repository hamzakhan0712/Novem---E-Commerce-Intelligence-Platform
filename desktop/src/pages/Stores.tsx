import { useEffect, useState } from 'react';

import {
  Button, Form, Input, Modal, Popconfirm, Select, Tag, message, Spin,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ShopOutlined, CheckCircleFilled, LinkOutlined,
  CalendarOutlined, CloudUploadOutlined, GlobalOutlined,
} from '@ant-design/icons';

import { useStoreStore } from '@/stores/storeStore';

import type { Store, CreateStoreRequest, UpdateStoreRequest } from '@/types/store';

import styles from './Stores.module.css';

const PLATFORMS = [
  { value: 'shopify', label: 'Shopify' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'etsy', label: 'Etsy' },
  { value: 'ebay', label: 'eBay' },
  { value: 'bigcommerce', label: 'BigCommerce' },
  { value: 'squarespace', label: 'Squarespace' },
  { value: 'custom', label: 'Custom / Other' },
];

const CURRENCIES = [
  { value: 'INR', label: 'INR — Indian Rupee' },
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'CAD', label: 'CAD — Canadian Dollar' },
  { value: 'AUD', label: 'AUD — Australian Dollar' },
  { value: 'JPY', label: 'JPY — Japanese Yen' },
  { value: 'PKR', label: 'PKR — Pakistani Rupee' },
  { value: 'AED', label: 'AED — UAE Dirham' },
  { value: 'SAR', label: 'SAR — Saudi Riyal' },
  { value: 'CNY', label: 'CNY — Chinese Yuan' },
  { value: 'BRL', label: 'BRL — Brazilian Real' },
];

const INDUSTRIES = [
  { value: 'fashion', label: 'Fashion & Apparel' },
  { value: 'electronics', label: 'Electronics' },
  { value: 'home_garden', label: 'Home & Garden' },
  { value: 'beauty', label: 'Beauty & Personal Care' },
  { value: 'food', label: 'Food & Beverage' },
  { value: 'health', label: 'Health & Wellness' },
  { value: 'sports', label: 'Sports & Outdoors' },
  { value: 'general', label: 'General / Other' },
];

function formatPlatform(p: string) {
  return PLATFORMS.find((o) => o.value === p)?.label ?? p;
}

function StoreListItem({ store, isActive, isSelected, onSelect }: {
  store: Store;
  isActive: boolean;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`${styles.storeTab} ${isSelected ? styles.storeTabSelected : ''} ${isActive ? styles.storeTabActive : ''}`}
      onClick={onSelect}
    >
      <div className={styles.tabIcon}>
        <ShopOutlined />
      </div>
      <div className={styles.tabInfo}>
        <span className={styles.tabName}>{store.name}</span>
        <span className={styles.tabMeta}>
          {formatPlatform(store.platform)} · {store.currency}
        </span>
      </div>
      {isActive && <Tag color="green" className={styles.activeTag}>Active</Tag>}
    </button>
  );
}

function StoreDetail({ store, isActive, onActivate, onEdit, onDelete }: {
  store: Store;
  isActive: boolean;
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const counts = store.data_summary;

  return (
    <div className={styles.detail}>
      <div className={styles.detailHeader}>
        <div className={styles.detailTitle}>
          <div className={styles.detailIcon}><ShopOutlined /></div>
          <div>
            <h2 className={styles.detailName}>{store.name}</h2>
            <div className={styles.detailTags}>
              {isActive && <Tag color="green">Active</Tag>}
              <Tag>{formatPlatform(store.platform)}</Tag>
              <Tag>{store.currency}</Tag>
              {store.industry && store.industry !== 'general' && (
                <Tag>{INDUSTRIES.find((i) => i.value === store.industry)?.label ?? store.industry}</Tag>
              )}
            </div>
          </div>
        </div>
        <div className={styles.detailActions}>
          {!isActive && (
            <Button type="primary" ghost onClick={onActivate} icon={<CheckCircleFilled />}>
              Set Active
            </Button>
          )}
          <Button icon={<EditOutlined />} onClick={onEdit}>Edit</Button>
          <Popconfirm title="Delete this store permanently?" onConfirm={onDelete}>
            <Button danger icon={<DeleteOutlined />}>Delete</Button>
          </Popconfirm>
        </div>
      </div>

      {store.url && (
        <div className={styles.detailUrl}>
          <LinkOutlined /> {store.url}
        </div>
      )}
      {store.description && (
        <p className={styles.detailDesc}>{store.description}</p>
      )}

      <div className={styles.detailSection}>
        <h3 className={styles.sectionLabel}>Data Summary</h3>
        <div className={styles.detailStats}>
          <div className={styles.stat}>
            <span className={styles.statValue}>{(counts?.orders ?? 0).toLocaleString()}</span>
            <span className={styles.statLabel}>Orders</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statValue}>{(counts?.customers ?? 0).toLocaleString()}</span>
            <span className={styles.statLabel}>Customers</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statValue}>{(counts?.products ?? 0).toLocaleString()}</span>
            <span className={styles.statLabel}>Products</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statValue}>{(counts?.reviews ?? 0).toLocaleString()}</span>
            <span className={styles.statLabel}>Reviews</span>
          </div>
        </div>
      </div>

      <div className={styles.detailSection}>
        <h3 className={styles.sectionLabel}>Configuration</h3>
        <div className={styles.configGrid}>
          <div className={styles.configItem}>
            <span className={styles.configLabel}>Platform</span>
            <span className={styles.configValue}>{formatPlatform(store.platform)}</span>
          </div>
          <div className={styles.configItem}>
            <span className={styles.configLabel}>Currency</span>
            <span className={styles.configValue}>{store.currency}</span>
          </div>
          <div className={styles.configItem}>
            <span className={styles.configLabel}>Industry</span>
            <span className={styles.configValue}>{INDUSTRIES.find((i) => i.value === store.industry)?.label ?? 'General'}</span>
          </div>
          <div className={styles.configItem}>
            <span className={styles.configLabel}>Status</span>
            <span className={styles.configValue}>{isActive ? 'Active' : 'Inactive'}</span>
          </div>
        </div>
      </div>

      <div className={styles.detailSection}>
        <h3 className={styles.sectionLabel}>Timeline</h3>
        <div className={styles.configGrid}>
          <div className={styles.configItem}>
            <span className={styles.configLabel}>Created</span>
            <span className={styles.configValue}>
              <CalendarOutlined /> {new Date(store.created_at).toLocaleDateString()}
            </span>
          </div>
          {counts?.last_import_at && (
            <div className={styles.configItem}>
              <span className={styles.configLabel}>Last Import</span>
              <span className={styles.configValue}>
                <CloudUploadOutlined /> {new Date(counts.last_import_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Stores() {
  const stores = useStoreStore((s) => s.stores);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const loading = useStoreStore((s) => s.loading);
  const fetchStores = useStoreStore((s) => s.fetchStores);
  const createStore = useStoreStore((s) => s.createStore);
  const updateStore = useStoreStore((s) => s.updateStore);
  const deleteStore = useStoreStore((s) => s.deleteStore);
  const setActiveStore = useStoreStore((s) => s.setActiveStore);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStore, setEditingStore] = useState<Store | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  const openCreate = () => {
    setEditingStore(null);
    form.resetFields();
    form.setFieldsValue({ platform: 'shopify', currency: 'INR', industry: 'general' });
    setModalOpen(true);
  };

  const openEdit = (store: Store) => {
    setEditingStore(store);
    form.setFieldsValue({
      name: store.name,
      platform: store.platform,
      url: store.url,
      currency: store.currency,
      industry: store.industry,
      description: store.description,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingStore) {
        const req: UpdateStoreRequest = { ...values };
        await updateStore(editingStore.id, req);
        message.success('Store updated');
      } else {
        const req: CreateStoreRequest = { ...values };
        await createStore(req);
        message.success('Store created');
      }
      setModalOpen(false);
      fetchStores();
    } catch {
      // Validation errors shown by form
    }
  };

  const handleDelete = async (storeId: string) => {
    await deleteStore(storeId);
    message.success('Store deleted');
  };

  // Sort: active store first
  const sorted = [...stores].sort((a, b) => {
    if (a.id === activeStoreId) return -1;
    if (b.id === activeStoreId) return 1;
    return 0;
  });

  // Auto-select first store if none selected
  const effectiveSelected = selectedStoreId && stores.find((s) => s.id === selectedStoreId)
    ? selectedStoreId
    : sorted[0]?.id ?? null;
  const selectedStore = stores.find((s) => s.id === effectiveSelected) ?? null;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Store Management</h1>
          <span className={styles.subtitle}>
            {stores.length} store{stores.length !== 1 ? 's' : ''} configured
          </span>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          New Store
        </Button>
      </div>

      {loading && stores.length === 0 ? (
        <div className={styles.emptyState}><Spin /></div>
      ) : stores.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIconWrap}>
            <GlobalOutlined className={styles.emptyIcon} />
          </div>
          <h3 className={styles.emptyTitle}>No stores yet</h3>
          <p className={styles.emptyDesc}>Create your first store to start importing data and generating insights.</p>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Create Store</Button>
        </div>
      ) : (
        <div className={styles.splitLayout}>
          <div className={styles.sidebar}>
            {sorted.map((store) => (
              <StoreListItem
                key={store.id}
                store={store}
                isActive={store.id === activeStoreId}
                isSelected={store.id === effectiveSelected}
                onSelect={() => setSelectedStoreId(store.id)}
              />
            ))}
          </div>
          <div className={styles.detailPanel}>
            {selectedStore ? (
              <StoreDetail
                store={selectedStore}
                isActive={selectedStore.id === activeStoreId}
                onActivate={() => setActiveStore(selectedStore.id)}
                onEdit={() => openEdit(selectedStore)}
                onDelete={() => handleDelete(selectedStore.id)}
              />
            ) : (
              <div className={styles.emptyDetail}>
                <ShopOutlined style={{ fontSize: 32, opacity: 0.3 }} />
                <p>Select a store to view details</p>
              </div>
            )}
          </div>
        </div>
      )}

      <Modal
        title={editingStore ? 'Edit Store' : 'Create Store'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editingStore ? 'Save' : 'Create'}
        confirmLoading={loading}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Store Name" rules={[{ required: true, message: 'Enter a store name' }]}>
            <Input placeholder="My Store" />
          </Form.Item>
          <Form.Item name="platform" label="Platform" rules={[{ required: true }]}>
            <Select options={PLATFORMS} />
          </Form.Item>
          <Form.Item name="url" label="Store URL">
            <Input placeholder="https://my-store.com" />
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Form.Item name="currency" label="Currency">
              <Select options={CURRENCIES} />
            </Form.Item>
            <Form.Item name="industry" label="Industry">
              <Select options={INDUSTRIES} />
            </Form.Item>
          </div>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Optional notes about this store" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
