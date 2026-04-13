import { useState, useEffect } from 'react';

import { Card, Form, Input, InputNumber, Switch, Button, message, Tag } from 'antd';
import { MailOutlined, SendOutlined, CheckCircleOutlined } from '@ant-design/icons';

import apiClient from '@/utils/apiClient';

import styles from './EmailSettings.module.css';

interface EmailConfig {
  configured: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  from_name?: string;
  from_email?: string;
  use_tls?: boolean;
}

export default function EmailSettings() {
  const [config, setConfig] = useState<EmailConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    try {
      const res = await apiClient.get('/email/config');
      if (res.data.success && res.data.data) {
        setConfig(res.data.data);
        if (res.data.data.configured) {
          form.setFieldsValue(res.data.data);
        }
      }
    } catch {
      // Config not available
    }
  }

  async function handleSave(values: Record<string, unknown>) {
    setLoading(true);
    try {
      const res = await apiClient.post('/email/config', values);
      if (res.data.success) {
        message.success('Email configuration saved');
        loadConfig();
      }
    } catch {
      message.error('Failed to save email configuration');
    } finally {
      setLoading(false);
    }
  }

  async function handleTest() {
    setTestResult(null);
    try {
      const res = await apiClient.post('/email/test');
      if (res.data.success && res.data.data?.success) {
        setTestResult('success');
        message.success('SMTP connection successful');
      } else {
        setTestResult(res.data.data?.error || 'Connection failed');
        message.error(res.data.data?.error || 'Connection test failed');
      }
    } catch {
      setTestResult('Connection test failed');
      message.error('Failed to test email connection');
    }
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>
        <MailOutlined /> Email Alerts
      </h2>
      <p className={styles.sectionDesc}>
        Configure SMTP to receive activity digest emails with business intelligence summaries.
      </p>

      <Card title="SMTP Configuration" size="small">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{ smtp_port: 587, use_tls: true, from_name: 'NOVEM' }}
        >
          <div className={styles.formGrid}>
            <Form.Item name="smtp_host" label="SMTP Host" rules={[{ required: true }]}>
              <Input placeholder="smtp.gmail.com" />
            </Form.Item>
            <Form.Item name="smtp_port" label="SMTP Port" rules={[{ required: true }]}>
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="smtp_user" label="SMTP Username" rules={[{ required: true }]}>
              <Input placeholder="user@example.com" />
            </Form.Item>
            <Form.Item name="smtp_password" label="SMTP Password" rules={[{ required: true }]}>
              <Input.Password placeholder="App password or SMTP password" />
            </Form.Item>
            <Form.Item name="from_name" label="From Name">
              <Input placeholder="NOVEM" />
            </Form.Item>
            <Form.Item name="from_email" label="From Email" rules={[{ required: true, type: 'email' }]}>
              <Input placeholder="alerts@yourstore.com" />
            </Form.Item>
          </div>
          <Form.Item name="use_tls" label="Use TLS" valuePropName="checked">
            <Switch />
          </Form.Item>

          <div className={styles.buttonRow}>
            <Button type="primary" htmlType="submit" loading={loading} icon={<CheckCircleOutlined />}>
              Save Configuration
            </Button>
            <Button onClick={handleTest} icon={<SendOutlined />} disabled={!config?.configured}>
              Test Connection
            </Button>
            {testResult && (
              <Tag color={testResult === 'success' ? 'green' : 'red'}>
                {testResult === 'success' ? 'Connection OK' : testResult}
              </Tag>
            )}
          </div>
        </Form>
      </Card>

      {config?.configured && (
        <Card title="Current Status" size="small" style={{ marginTop: 16 }}>
          <Tag color="green" icon={<CheckCircleOutlined />}>Configured</Tag>
          <span style={{ marginLeft: 8, color: 'var(--novem-text-secondary)' }}>
            {config.smtp_host}:{config.smtp_port} ({config.smtp_user})
          </span>
        </Card>
      )}
    </div>
  );
}
