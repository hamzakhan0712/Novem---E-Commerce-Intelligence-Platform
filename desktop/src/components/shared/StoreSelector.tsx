import { useState } from 'react';

import { Select, Modal, Input, Form, message } from 'antd';
import { PlusOutlined, ShopOutlined } from '@ant-design/icons';

import { useStoreStore } from '@/stores/storeStore';
import { useStores } from '@/hooks/useStores';
import type { CreateStoreRequest } from '@/types/store';

import styles from './StoreSelector.module.css';

const PLATFORMS = [
  { value: 'shopify', label: 'Shopify' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'etsy', label: 'Etsy' },
  { value: 'ebay', label: 'eBay' },
  { value: 'bigcommerce', label: 'BigCommerce' },
  { value: 'squarespace', label: 'Squarespace' },
  { value: 'custom', label: 'Custom / Other' },
];

export default function StoreSelector() {
  const { stores, activeStoreId, loading } = useStores();
  const setActiveStore = useStoreStore((s) => s.setActiveStore);
  const createStore = useStoreStore((s) => s.createStore);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      const req: CreateStoreRequest = {
        name: values.name.trim(),
        platform: values.platform,
      };
      const store = await createStore(req);
      if (store) {
        message.success(`Store "${store.name}" created`);
        setIsModalOpen(false);
        form.resetFields();
      }
    } catch {
      // validation error
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className={styles.storeSelector}>
      <ShopOutlined style={{ fontSize: 13, color: 'var(--novem-text-secondary)' }} />
      <Select
        className={styles.select}
        size="small"
        value={activeStoreId}
        onChange={setActiveStore}
        loading={loading}
        placeholder="Select a store"
        options={stores.map((s) => ({
          value: s.id,
          label: s.name,
        }))}
        notFoundContent="No stores yet"
      />
      <button
        className={styles.addBtn}
        onClick={() => setIsModalOpen(true)}
        title="Add store"
      >
        <PlusOutlined />
      </button>

      <Modal
        title="Create a new store"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="Create"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Store name"
            rules={[{ required: true, message: 'Give your store a name' }]}
          >
            <Input placeholder="e.g. My Shopify Store" autoFocus />
          </Form.Item>
          <Form.Item
            name="platform"
            label="Platform"
            initialValue="custom"
          >
            <Select options={PLATFORMS} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
