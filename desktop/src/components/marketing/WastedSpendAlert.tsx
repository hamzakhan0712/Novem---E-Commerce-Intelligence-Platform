import { Alert, Space, Tag, Tooltip } from 'antd';
import { WarningOutlined } from '@ant-design/icons';

import type { WastedSpendData } from '@/types/marketing';
import { formatCurrency } from '@/utils/formatCurrency';

import styles from './WastedSpendAlert.module.css';

interface WastedSpendAlertProps {
  data: WastedSpendData | null;
}

export default function WastedSpendAlert({ data }: WastedSpendAlertProps) {
  if (!data || !data.alerts.length) return null;

  return (
    <Alert
      type="warning"
      showIcon
      icon={<WarningOutlined />}
      className={styles.alert}
      message={
        <span className={styles.title}>
          Wasted Ad Spend Detected — {formatCurrency(data.total_wasted_spend)} across {data.total_campaigns_flagged} campaign(s)
        </span>
      }
      description={
        <Space direction="vertical" size={4} className={styles.body}>
          {data.alerts.map((a) => (
            <div key={`${a.channel}-${a.campaign_name}`} className={styles.row}>
              <Tag color="orange">{a.channel.replace('_', ' ')}</Tag>
              <span className={styles.campaign}>{a.campaign_name}</span>
              <span className={styles.spend}>{formatCurrency(a.spend)}</span>
              <Tooltip title={a.out_of_stock_products.join(', ')}>
                <Tag color="red">{a.out_of_stock_products.length} OOS product(s)</Tag>
              </Tooltip>
            </div>
          ))}
        </Space>
      }
    />
  );
}
