import { useState, useEffect, useRef } from 'react';

import { Button, Checkbox, Divider, Form, Input, message, Steps, Alert, Collapse, Tag, Progress, List, Select } from 'antd';
import {
  ShopOutlined, CheckCircleFilled, CloseCircleFilled,
  LinkOutlined, CopyOutlined, SyncOutlined, InfoCircleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

import styles from './ShopifyConnector.module.css';

type SyncDataType = 'orders' | 'customers' | 'products' | 'reviews' | 'stock_levels';

interface SyncResultItem {
  data_type: string;
  row_count_raw: number;
  status: string;
  imported_at: string;
}

export default function ShopifyConnector() {
  const [form] = Form.useForm();
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const startGlobalSync = useSyncStore((s) => s.startSync);
  const endGlobalSync = useSyncStore((s) => s.endSync);
  const notifyDataChanged = useSyncStore((s) => s.notifyDataChanged);

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<boolean | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResults, setSyncResults] = useState<SyncResultItem[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<SyncDataType[]>(['orders', 'customers', 'products']);

  const [webhookInfo, setWebhookInfo] = useState<{
    webhook_url: string; full_url: string; webhook_secret: string; instructions: string;
  } | null>(null);
  const [configuringWebhook, setConfiguringWebhook] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [testWebhookTopic, setTestWebhookTopic] = useState('products/create');
  const [testWebhookResult, setTestWebhookResult] = useState<{ status: string; message: string; rows: number } | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const currentStep = testResult === null ? 0 : testResult ? 1 : 0;

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields(['shop_domain', 'api_key', 'api_secret']);
      setTesting(true);
      setTestResult(null);
      const res = await apiClient.post('/connectors/test-connection', {
        credential_type: 'shopify_api',
        credentials: values,
      });
      const connected = res.data?.data?.connected ?? false;
      setTestResult(connected);

      if (connected) {
        message.success('Shopify connection successful');
        if (activeStoreId) {
          await apiClient.post('/credentials', {
            store_id: activeStoreId,
            credential_type: 'shopify_api',
            credentials: values,
          });
        }
      } else {
        message.error(res.data?.data?.message || 'Connection failed');
      }
    } catch {
      setTestResult(false);
      message.error('Connection test failed');
    } finally {
      setTesting(false);
    }
  };

  const pollSyncResults = () => {
    if (!activeStoreId) return;
    const startedAt = Date.now();
    pollRef.current = setInterval(async () => {
      try {
        const res = await apiClient.get(`/sync/history/${activeStoreId}?limit=10`);
        const items: SyncResultItem[] = res.data?.data ?? [];
        const recentItems = items.filter(
          (i) => new Date(i.imported_at).getTime() > startedAt - 5000
        );
        if (recentItems.length > 0) {
          setSyncResults(recentItems);
        }
        // Stop polling after 60s or when we get results
        if (Date.now() - startedAt > 60000 || recentItems.length >= selectedTypes.length) {
          if (pollRef.current) clearInterval(pollRef.current);
          setSyncing(false);
          endGlobalSync();
        }
      } catch {
        // keep polling
      }
    }, 3000);
  };

  const handleSync = async () => {
    if (!activeStoreId) {
      message.error('Select a store first');
      return;
    }
    if (selectedTypes.length === 0) {
      message.warning('Select at least one data type');
      return;
    }
    setSyncing(true);
    setSyncResults([]);
    startGlobalSync('Syncing Shopify data…');
    try {
      await apiClient.post('/connectors/sync', {
        store_id: activeStoreId,
        data_types: selectedTypes,
      });
      message.info('Sync initiated — fetching data from Shopify…');
      pollSyncResults();
    } catch {
      message.error('Sync failed');
      setSyncing(false);
      endGlobalSync();
    }
  };

  const handleConfigureWebhook = async () => {
    if (!activeStoreId) return;
    setConfiguringWebhook(true);
    try {
      const res = await apiClient.post(`/webhooks/configure/${activeStoreId}?platform=shopify`);
      setWebhookInfo(res.data?.data ?? null);
      message.success('Webhook configured');
    } catch {
      message.error('Failed to configure webhook');
    } finally {
      setConfiguringWebhook(false);
    }
  };

  const handleTestWebhook = async () => {
    if (!activeStoreId) return;
    setTestingWebhook(true);
    setTestWebhookResult(null);
    try {
      const res = await apiClient.post(`/webhooks/test/${activeStoreId}?topic=${encodeURIComponent(testWebhookTopic)}`);
      const data = res.data?.data;
      setTestWebhookResult(data ?? null);
      message.success(data?.message || 'Test webhook processed');
      notifyDataChanged();
    } catch {
      setTestWebhookResult({ status: 'error', message: 'Test webhook failed — check engine logs', rows: 0 });
      message.error('Test webhook failed');
    } finally {
      setTestingWebhook(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('Copied to clipboard');
  };

  const totalSyncedRows = syncResults.reduce((sum, r) => sum + (r.row_count_raw ?? 0), 0);

  return (
    <div className={styles.connectorForm}>
      <div className={styles.connectorHeader}>
        <ShopOutlined style={{ fontSize: 24, color: '#96bf48' }} />
        <div>
          <h3 className={styles.connectorTitle}>Shopify</h3>
          <span className={styles.connectorDesc}>Connect via REST Admin API & Webhooks</span>
        </div>
        {testResult !== null && (
          <span className={styles.statusBadge}>
            {testResult
              ? <><CheckCircleFilled style={{ color: 'var(--novem-success)' }} /> Connected</>
              : <><CloseCircleFilled style={{ color: 'var(--novem-error)' }} /> Failed</>}
          </span>
        )}
      </div>

      <Steps
        size="small"
        current={currentStep}
        items={[
          { title: 'Connect' },
          { title: 'Sync Data' },
          { title: 'Webhooks (Optional)' },
        ]}
        style={{ marginBottom: 20 }}
      />

      {/* Step 1: Credentials */}
      <Form form={form} layout="vertical">
        <Form.Item
          name="shop_domain"
          label="Shop Domain"
          rules={[{ required: true, message: 'Enter your Shopify domain' }]}
          extra="e.g. my-store.myshopify.com"
        >
          <Input placeholder="my-store.myshopify.com" />
        </Form.Item>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: true, message: 'Enter the API key' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="api_secret"
            label="Admin Access Token"
            rules={[{ required: true, message: 'Enter the access token' }]}
          >
            <Input.Password />
          </Form.Item>
        </div>

        <div className={styles.formActions}>
          <Button
            icon={<LinkOutlined />}
            onClick={handleTestConnection}
            loading={testing}
          >
            Test Connection
          </Button>
        </div>
      </Form>

      {/* Step 2: Sync */}
      {testResult && (
        <>
          <Divider style={{ margin: '16px 0' }} />
          <h4 className={styles.sectionLabel}>Select data to sync</h4>
          <Checkbox.Group
            value={selectedTypes}
            onChange={(vals) => setSelectedTypes(vals as SyncDataType[])}
            style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}
          >
            <Checkbox value="orders">Orders</Checkbox>
            <Checkbox value="customers">Customers</Checkbox>
            <Checkbox value="products">Products</Checkbox>
            <Checkbox value="reviews">Reviews</Checkbox>
            <Checkbox value="stock_levels">Stock Levels</Checkbox>
          </Checkbox.Group>

          <div className={styles.formActions}>
            <Button
              type="primary"
              icon={syncing ? <SyncOutlined spin /> : undefined}
              onClick={handleSync}
              loading={syncing}
              disabled={!activeStoreId || selectedTypes.length === 0}
            >
              {syncing ? 'Syncing…' : 'Start Sync'}
            </Button>
          </div>

          {/* Sync progress / results */}
          {syncing && syncResults.length === 0 && (
            <div className={styles.syncProgress}>
              <SyncOutlined spin style={{ fontSize: 18, color: 'var(--novem-accent)' }} />
              <div>
                <p className={styles.syncProgressText}>Fetching data from Shopify…</p>
                <p className={styles.syncProgressSub}>
                  This may take a few minutes depending on your store size.
                </p>
              </div>
              <Progress percent={99.9} status="active" showInfo={false} style={{ maxWidth: 200 }} />
            </div>
          )}

          {syncResults.length > 0 && (
            <div className={styles.syncResults}>
              <div className={styles.syncResultsHeader}>
                <CheckCircleFilled style={{ color: 'var(--novem-success)', fontSize: 18 }} />
                <span>
                  Sync complete — <strong>{totalSyncedRows}</strong> total rows imported
                </span>
              </div>
              <List
                size="small"
                dataSource={syncResults}
                renderItem={(item) => (
                  <List.Item style={{ padding: '6px 0' }}>
                    <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{item.data_type}</span>
                    <span style={{ margin: '0 8px' }}>—</span>
                    <span>{item.row_count_raw} rows</span>
                    <Tag
                      color={item.status === 'completed' ? 'success' : 'error'}
                      style={{ marginLeft: 'auto' }}
                    >
                      {item.status}
                    </Tag>
                  </List.Item>
                )}
              />
            </div>
          )}
        </>
      )}

      {/* Step 3: Webhook setup */}
      {testResult && (
        <>
          <Divider style={{ margin: '16px 0' }} />
          <h4 className={styles.sectionLabel}>Real-time Webhooks</h4>
          <p className={styles.connectorDesc}>
            Configure a webhook so Shopify pushes new orders, customers, and product updates to NOVEM in real time.
          </p>

          {!webhookInfo ? (
            <Button onClick={handleConfigureWebhook} loading={configuringWebhook} disabled={!activeStoreId}>
              Generate Webhook URL &amp; Secret
            </Button>
          ) : (
            <div className={styles.webhookInfo}>
              <div className={styles.webhookField}>
                <span className={styles.webhookLabel}>Webhook URL (local)</span>
                <div className={styles.webhookValue}>
                  <code>{webhookInfo.full_url}</code>
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(webhookInfo.full_url)}
                  />
                </div>
              </div>
              <div className={styles.webhookField}>
                <span className={styles.webhookLabel}>Endpoint Path</span>
                <div className={styles.webhookValue}>
                  <code>{webhookInfo.webhook_url}</code>
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(webhookInfo.webhook_url)}
                  />
                </div>
              </div>
              <div className={styles.webhookField}>
                <span className={styles.webhookLabel}>HMAC Secret</span>
                <div className={styles.webhookValue}>
                  <code>{webhookInfo.webhook_secret}</code>
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(webhookInfo.webhook_secret)}
                  />
                </div>
              </div>

              <Alert
                type="warning"
                showIcon
                icon={<InfoCircleOutlined />}
                message="Webhooks require a public URL"
                description="Shopify can't reach localhost. Use a tunnel like ngrok to expose your server, then use the public URL with the endpoint path above."
                style={{ marginTop: 4 }}
              />

              <Divider style={{ margin: '14px 0' }} />
              <h4 className={styles.sectionLabel}>Test Webhook Pipeline</h4>
              <p className={styles.connectorDesc}>
                Send a mock payload through NOVEM's webhook pipeline to verify everything works end-to-end.
              </p>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <Select
                  value={testWebhookTopic}
                  onChange={setTestWebhookTopic}
                  style={{ width: 200 }}
                  options={[
                    { label: 'Product creation', value: 'products/create' },
                    { label: 'Order creation', value: 'orders/create' },
                    { label: 'Customer creation', value: 'customers/create' },
                  ]}
                />
                <Button
                  icon={<ExperimentOutlined />}
                  onClick={handleTestWebhook}
                  loading={testingWebhook}
                >
                  Send Test Webhook
                </Button>
              </div>
              {testWebhookResult && (
                <Alert
                  type={testWebhookResult.status === 'processed' ? 'success' : 'error'}
                  showIcon
                  message={testWebhookResult.status === 'processed' ? `Test passed — ${testWebhookResult.rows} row(s) inserted` : 'Test failed'}
                  description={testWebhookResult.message}
                  style={{ marginTop: 12 }}
                />
              )}

              <Divider style={{ margin: '14px 0' }} />

              <Collapse
                ghost
                items={[{
                  key: 'setup',
                  label: <span style={{ fontWeight: 600, fontSize: 13 }}>Step-by-step setup guide</span>,
                  children: (
                    <ol className={styles.setupSteps}>
                      <li>
                        <strong>Expose your local server</strong> — Run <code>ngrok http 44945</code> in a terminal.
                        Copy the <code>https://</code> forwarding URL (e.g. <code>https://abc123.ngrok.io</code>).
                      </li>
                      <li>
                        <strong>Open Shopify Admin</strong> — Go to <em>Settings → Notifications</em> and scroll to the
                        bottom to find <em>Webhooks</em>.
                      </li>
                      <li>
                        <strong>Create a webhook</strong> — Click "Create webhook". Select an event
                        (e.g. <code>Order creation</code>). Set format to <strong>JSON</strong>.
                      </li>
                      <li>
                        <strong>Paste the URL</strong> — Combine the ngrok URL with the endpoint path:
                        <br />
                        <code>{`https://YOUR_NGROK_DOMAIN${webhookInfo.webhook_url}`}</code>
                        <Button
                          size="small"
                          type="link"
                          icon={<CopyOutlined />}
                          onClick={() => copyToClipboard(webhookInfo.webhook_url)}
                        />
                      </li>
                      <li>
                        <strong>Recommended events</strong> — Create separate webhooks for:
                        <ul>
                          <li><code>Order creation</code> — new orders</li>
                          <li><code>Order updated</code> — status changes, fulfillment</li>
                          <li><code>Customer creation</code> — new customers</li>
                          <li><code>Customer update</code> — profile changes</li>
                          <li><code>Product creation</code> and <code>Product update</code></li>
                        </ul>
                      </li>
                      <li>
                        <strong>Verification</strong> — NOVEM automatically verifies each incoming webhook using the HMAC
                        secret. No extra setup needed.
                      </li>
                      <li>
                        <strong>Test it</strong> — Click "Send test notification" in Shopify for any webhook. Check the
                        Sync Activity tab in the notification drawer to confirm it arrived.
                      </li>
                    </ol>
                  ),
                }]}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
