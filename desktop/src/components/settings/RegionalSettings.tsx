import { Select } from 'antd';

import { useSettingsStore } from '@/stores/settingsStore';

import styles from './GeneralSettings.module.css';

const CURRENCY_OPTIONS = [
  { value: 'INR', label: 'INR (₹)' },
  { value: 'USD', label: 'USD ($)' },
  { value: 'EUR', label: 'EUR (€)' },
  { value: 'GBP', label: 'GBP (£)' },
  { value: 'CAD', label: 'CAD (C$)' },
  { value: 'AUD', label: 'AUD (A$)' },
  { value: 'JPY', label: 'JPY (¥)' },
  { value: 'PKR', label: 'PKR (₨)' },
];

const DATE_FORMAT_OPTIONS = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
  { value: 'DD-MMM-YYYY', label: 'DD-MMM-YYYY' },
];

const FISCAL_MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: new Date(2024, i, 1).toLocaleString('en', { month: 'long' }),
}));

export default function RegionalSettings() {
  const currency = useSettingsStore((s) => s.currency);
  const dateFormat = useSettingsStore((s) => s.dateFormat);
  const fiscalYearStart = useSettingsStore((s) => s.fiscalYearStart);
  const updateSetting = useSettingsStore((s) => s.updateSetting);

  return (
    <div>
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Regional Preferences</div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Default Currency</span>
          </div>
          <div className={styles.formControl}>
            <Select
              value={currency}
              onChange={(val) => updateSetting('currency', val)}
              style={{ width: 140 }}
              options={CURRENCY_OPTIONS}
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Date Format</span>
          </div>
          <div className={styles.formControl}>
            <Select
              value={dateFormat}
              onChange={(val) => updateSetting('dateFormat', val)}
              style={{ width: 160 }}
              options={DATE_FORMAT_OPTIONS}
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Fiscal Year Start</span>
          </div>
          <div className={styles.formControl}>
            <Select
              value={fiscalYearStart}
              onChange={(val) => updateSetting('fiscalYearStart', val)}
              style={{ width: 160 }}
              options={FISCAL_MONTH_OPTIONS}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
