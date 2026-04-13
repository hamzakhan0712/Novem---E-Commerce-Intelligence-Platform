import { useState, useEffect, useRef } from 'react';

import { Input, Button, Select, message } from 'antd';
import { SaveOutlined, CameraOutlined } from '@ant-design/icons';

import { useAuthStore } from '@/stores/authStore';
import { useSettingsStore } from '@/stores/settingsStore';

import styles from './ProfileSettings.module.css';

const REGION_OPTIONS = [
  { value: 'US', label: 'United States' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'EU', label: 'Europe' },
  { value: 'CA', label: 'Canada' },
  { value: 'AU', label: 'Australia' },
  { value: 'IN', label: 'India' },
  { value: 'PK', label: 'Pakistan' },
  { value: 'AE', label: 'UAE' },
  { value: 'SA', label: 'Saudi Arabia' },
  { value: 'JP', label: 'Japan' },
  { value: 'CN', label: 'China' },
  { value: 'BR', label: 'Brazil' },
  { value: 'OTHER', label: 'Other' },
];

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

const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Eastern (US)' },
  { value: 'America/Chicago', label: 'Central (US)' },
  { value: 'America/Denver', label: 'Mountain (US)' },
  { value: 'America/Los_Angeles', label: 'Pacific (US)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)' },
  { value: 'Asia/Karachi', label: 'Karachi (PKT)' },
  { value: 'Asia/Kolkata', label: 'Kolkata (IST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
];

const FISCAL_MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: new Date(2024, i, 1).toLocaleString('en', { month: 'long' }),
}));

export default function ProfileSettings() {
  const { user, loading, error, updateProfile, clearError } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [currency, setCurrency] = useState(user?.currency ?? 'USD');
  const [region, setRegion] = useState(user?.region ?? '');
  const [dateFormat, setDateFormat] = useState(user?.date_format ?? 'YYYY-MM-DD');
  const [fiscalYearStart, setFiscalYearStart] = useState(user?.fiscal_year_start ?? '1');
  const [timezone, setTimezone] = useState(user?.timezone ?? 'UTC');
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setEmail(user.email ?? '');
      setCurrency(user.currency ?? 'USD');
      setRegion(user.region ?? '');
      setDateFormat(user.date_format ?? 'YYYY-MM-DD');
      setFiscalYearStart(user.fiscal_year_start ?? '1');
      setTimezone(user.timezone ?? 'UTC');
    }
  }, [user]);

  const avatarSeed = user?.avatar_seed ?? user?.name ?? 'user';
  const dicebearUrl = `https://api.dicebear.com/7.x/adventurer/svg?seed=${encodeURIComponent(avatarSeed)}`;
  const storedPhoto = user?.avatar_photo ?? null;
  const displayAvatar = avatarPreview ?? storedPhoto ?? dicebearUrl;
  const initials = (user?.name ?? 'U')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const hasProfileChanges =
    name !== (user?.name ?? '') ||
    email !== (user?.email ?? '') ||
    currency !== (user?.currency ?? 'USD') ||
    region !== (user?.region ?? '') ||
    dateFormat !== (user?.date_format ?? 'YYYY-MM-DD') ||
    fiscalYearStart !== (user?.fiscal_year_start ?? '1') ||
    timezone !== (user?.timezone ?? 'UTC') ||
    avatarPreview !== null;

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      message.error('Please select an image file');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setAvatarPreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSaveProfile = async () => {
    if (!hasProfileChanges) return;
    await updateProfile({
      name: name.trim(),
      email: email.trim() || null,
      currency,
      region: region.trim(),
      date_format: dateFormat,
      fiscal_year_start: fiscalYearStart,
      timezone,
      ...(avatarPreview ? { avatar_photo: avatarPreview } : {}),
    });
    // Sync regional settings to the settings store
    const updateSetting = useSettingsStore.getState().updateSetting;
    await Promise.all([
      updateSetting('currency', currency),
      updateSetting('date_format', dateFormat),
      updateSetting('fiscal_year_start', fiscalYearStart),
      updateSetting('region', region),
    ]);
    if (!error) {
      message.success('Profile updated');
      setAvatarPreview(null);
    }
  };

  return (
    <div className={styles.profileSection}>
      <div className={styles.profileHeader}>
        <div className={styles.avatarWrapper} onClick={handleAvatarClick}>
          {displayAvatar ? (
            <img src={displayAvatar} alt="" className={styles.avatar} />
          ) : (
            <div className={styles.avatarFallback}>{initials}</div>
          )}
          <div className={styles.avatarOverlay}>
            <CameraOutlined />
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleAvatarChange}
            style={{ display: 'none' }}
          />
        </div>
        <div className={styles.profileInfo}>
          <h3 className={styles.profileName}>{user?.name ?? 'User'}</h3>
          {user?.email && <p className={styles.profileEmail}>{user.email}</p>}
          <div className={styles.profileMeta}>
            {user?.created_at && <span>Joined {new Date(user.created_at).toLocaleDateString()}</span>}
            {user?.email_verified && <span>· Email verified</span>}
          </div>
        </div>
      </div>

      <div className={styles.divider} />

      <div>
        <h4 className={styles.sectionTitle}>Personal Information</h4>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Name</label>
            <Input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (error) clearError();
              }}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Email</label>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Region</label>
            <Select
              value={region || undefined}
              onChange={setRegion}
              options={REGION_OPTIONS}
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="label"
              placeholder="Select region"
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Timezone</label>
            <Select
              value={timezone}
              onChange={setTimezone}
              options={TIMEZONE_OPTIONS}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </div>

      <div className={styles.divider} />

      <div>
        <h4 className={styles.sectionTitle}>Preferences</h4>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Currency</label>
            <Select
              value={currency}
              onChange={setCurrency}
              options={CURRENCY_OPTIONS}
              style={{ width: '100%' }}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Date Format</label>
            <Select
              value={dateFormat}
              onChange={setDateFormat}
              options={DATE_FORMAT_OPTIONS}
              style={{ width: '100%' }}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Fiscal Year Start</label>
            <Select
              value={fiscalYearStart}
              onChange={setFiscalYearStart}
              options={FISCAL_MONTH_OPTIONS}
              style={{ width: '100%' }}
            />
          </div>
        </div>
        <div className={styles.actions} style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSaveProfile}
            loading={loading}
            disabled={!hasProfileChanges || !name.trim()}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
