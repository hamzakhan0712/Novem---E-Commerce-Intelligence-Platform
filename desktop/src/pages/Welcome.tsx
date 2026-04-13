import { useState, useRef } from 'react';

import { Button, Input, Select, Steps, message } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  ShopOutlined,
  AppstoreOutlined,
  ArrowRightOutlined,
  ArrowLeftOutlined,
  QuestionCircleOutlined,
  GlobalOutlined,
  RocketOutlined,
  DashboardOutlined,
  LineChartOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  CameraOutlined,
} from '@ant-design/icons';

import { useAuthStore } from '@/stores/authStore';
import { useStoreStore } from '@/stores/storeStore';
import { useAppStore } from '@/stores/appStore';
import { useSettingsStore } from '@/stores/settingsStore';
import TitleBar from '@/components/shell/TitleBar';
import novemLogo from '@/assets/images/novem_logo.png';

import welcomeDark from '@/assets/images/welcome_dark.png';
import welcomeLight from '@/assets/images/welcome_light.png';
import type { SetupRequest } from '@/types/auth';
import type { CreateStoreRequest } from '@/types/store';

import styles from './Welcome.module.css';

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

const REGIONS = [
  { value: 'IN', label: 'India' },
  { value: 'US', label: 'United States' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'EU', label: 'Europe' },
  { value: 'CA', label: 'Canada' },
  { value: 'AU', label: 'Australia' },
  { value: 'PK', label: 'Pakistan' },
  { value: 'AE', label: 'UAE' },
  { value: 'SA', label: 'Saudi Arabia' },
  { value: 'JP', label: 'Japan' },
  { value: 'CN', label: 'China' },
  { value: 'BR', label: 'Brazil' },
  { value: 'OTHER', label: 'Other' },
];

const TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'America/New_York', label: 'Eastern (US)' },
  { value: 'America/Chicago', label: 'Central (US)' },
  { value: 'America/Denver', label: 'Mountain (US)' },
  { value: 'America/Los_Angeles', label: 'Pacific (US)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Central Europe' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)' },
  { value: 'Asia/Karachi', label: 'Pakistan (PKT)' },
  { value: 'Asia/Shanghai', label: 'China (CST)' },
  { value: 'Asia/Tokyo', label: 'Japan (JST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
];

const DATE_FORMATS = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
  { value: 'DD-MMM-YYYY', label: 'DD-MMM-YYYY' },
];

const FISCAL_MONTHS = Array.from({ length: 12 }, (_, i) => ({
  value: new Date(2024, i, 1).toLocaleString('en', { month: 'long' }).toLowerCase(),
  label: new Date(2024, i, 1).toLocaleString('en', { month: 'long' }),
}));

const PLATFORMS = [
  { value: 'shopify', label: 'Shopify' },
  { value: 'custom', label: 'Custom / Other' },
];

const INDUSTRIES = [
  { value: 'fashion', label: 'Fashion & Apparel' },
  { value: 'electronics', label: 'Electronics' },
  { value: 'home_garden', label: 'Home & Garden' },
  { value: 'beauty', label: 'Beauty & Personal Care' },
  { value: 'food', label: 'Food & Beverage' },
  { value: 'health', label: 'Health & Wellness' },
  { value: 'sports', label: 'Sports & Outdoors' },
  { value: 'toys', label: 'Toys & Games' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'general', label: 'General / Other' },
];

const SECURITY_QUESTIONS = [
  'What was the name of your first pet?',
  'What city were you born in?',
  'What is your mother\'s maiden name?',
  'What was the name of your first school?',
  'What is your favorite book?',
];

function getPasswordStrength(pw: string): 'weak' | 'fair' | 'good' {
  if (pw.length < 8) return 'weak';
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score >= 3) return 'good';
  if (score >= 1) return 'fair';
  return 'weak';
}

export default function Welcome() {
  const { loading, error, setup, setAuth, clearError } = useAuthStore();
  const createStore = useStoreStore((s) => s.createStore);
  const themeMode = useAppStore((s) => s.themeMode);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(0);

  // Step 0: Profile
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [securityQuestion, setSecurityQuestion] = useState(SECURITY_QUESTIONS[0]);
  const [securityAnswer, setSecurityAnswer] = useState('');
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  // Step 1: Preferences
  const [region, setRegion] = useState('IN');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [dateFormat, setDateFormat] = useState('DD/MM/YYYY');
  const [fiscalYearStart, setFiscalYearStart] = useState('april');

  // Step 2: Store
  const [storeName, setStoreName] = useState('');
  const [platform, setPlatform] = useState('custom');
  const [industry, setIndustry] = useState('general');
  const [currency, setCurrency] = useState('INR');
  const [submitting, setSubmitting] = useState(false);

  const heroBg = themeMode === 'dark' ? welcomeDark : welcomeLight;

  const strength = password ? getPasswordStrength(password) : null;
  const passwordsMatch = confirmPassword ? password === confirmPassword : true;
  const isProfileValid = name.trim().length > 0 && password.length >= 8 && passwordsMatch;
  const isPrefsValid = true;
  const isStoreValid = storeName.trim().length > 0;

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
    reader.onload = () => setAvatarPreview(reader.result as string);
    reader.readAsDataURL(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleNext = () => {
    if (step === 0 && isProfileValid) setStep(1);
    else if (step === 1 && isPrefsValid) setStep(2);
    else if (step === 2 && isStoreValid) setStep(3);
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleSubmit = async () => {
    if (!isProfileValid || !isStoreValid) return;
    setSubmitting(true);

    const req: SetupRequest = {
      name: name.trim(),
      password,
      currency,
      region,
      timezone,
      date_format: dateFormat,
      fiscal_year_start: fiscalYearStart,
      security_question: securityQuestion,
      security_answer: securityAnswer.trim().toLowerCase() || undefined,
      ...(avatarPreview ? { avatar_photo: avatarPreview } : {}),
    };
    if (email.trim()) req.email = email.trim();

    try {
      const { token, user } = await setup(req);

      const storeReq: CreateStoreRequest = {
        name: storeName.trim(),
        platform,
        industry,
        currency,
      };
      await createStore(storeReq);

      // Sync currency & regional prefs to the settings store
      const updateSetting = useSettingsStore.getState().updateSetting;
      await Promise.all([
        updateSetting('currency', currency),
        updateSetting('date_format', dateFormat),
        updateSetting('fiscal_year_start', fiscalYearStart),
        updateSetting('region', region),
      ]);

      setAuth(token, user);
    } catch {
      message.error('Failed to complete setup');
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (step === 0 && isProfileValid) handleNext();
      else if (step === 1) handleNext();
      else if (step === 2 && isStoreValid) handleNext();
      else if (step === 3 && !submitting) handleSubmit();
    }
  };

  return (
    <div className={styles.welcome}>
      <TitleBar minimal />
      <div className={styles.body}>
        <div
          className={styles.heroSide}
          style={{ backgroundImage: `url(${heroBg})` }}
        >
          <div className={styles.heroBrand}>
            <img src={novemLogo} alt="NOVEM" className={styles.heroLogo} />
            <div className={styles.heroBrandText}>
              <h1 className={styles.heroTitle}>NOVEM</h1>
              <p className={styles.heroTagline}>E-Commerce Intelligence Platform</p>
            </div>
          </div>

          <div className={styles.heroFeaturesLarge}>
            <div className={styles.heroFeatureLarge}>
              <DashboardOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>Auto-Analysis &amp; KPI Dashboards</h3>
                <p className={styles.heroFeatureLargeDesc}>Revenue, customer value, order trends, and at-risk alerts — automatically generated the moment you import data.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <LineChartOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>Smart Forecasting</h3>
                <p className={styles.heroFeatureLargeDesc}>AI-powered predictions for sales, demand, and seasonal patterns with unusual activity detection built in.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <RobotOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>AI Copilot</h3>
                <p className={styles.heroFeatureLargeDesc}>Ask questions in plain English and get instant root-cause analysis powered by a local LLM — no cloud required.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <SafetyCertificateOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>100% Local &amp; Private</h3>
                <p className={styles.heroFeatureLargeDesc}>DuckDB analytics, SQLite storage, zero telemetry. Your data never leaves your machine — ever.</p>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.formSide}>
          <div className={styles.formContainer} onKeyDown={handleKeyDown}>
            <div className={styles.stepsWrapper}>
              <Steps
                current={step}
                size="small"
                items={[
                  { title: 'Profile' },
                  { title: 'Preferences' },
                  { title: 'Store' },
                  { title: 'Ready' },
                ]}
              />
            </div>

            {/* Step 0: Profile */}
            {step === 0 && (
              <div className={styles.stepContent}>
                <h2 className={styles.stepTitle}>Create your profile</h2>
                <p className={styles.stepDesc}>Set up your workspace credentials.</p>

                <div className={styles.form}>
                  {/* Avatar + identity row */}
                  <div className={styles.identityRow}>
                    <div className={styles.avatarUpload} onClick={handleAvatarClick}>
                      {avatarPreview ? (
                        <img src={avatarPreview} alt="" className={styles.avatarImg} />
                      ) : (
                        <div className={styles.avatarPlaceholder}>
                          <CameraOutlined className={styles.avatarPlaceholderIcon} />
                        </div>
                      )}
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleAvatarChange}
                        style={{ display: 'none' }}
                      />
                    </div>
                    <div className={styles.identityFields}>
                      <div className={styles.field}>
                        <label className={styles.label}>
                          Your name <span className={styles.required}>*</span>
                        </label>
                        <Input
                          prefix={<UserOutlined />}
                          placeholder="e.g. Sarah Chen"
                          value={name}
                          onChange={(e) => {
                            setName(e.target.value);
                            if (error) clearError();
                          }}
                          autoFocus
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Email</label>
                        <Input
                          prefix={<MailOutlined />}
                          placeholder="you@company.com (optional)"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Password group */}
                  <div className={styles.fieldGroup}>
                    <span className={styles.groupLabel}><LockOutlined /> Security</span>
                    <div className={styles.row}>
                      <div className={styles.field}>
                        <label className={styles.label}>
                          Password <span className={styles.required}>*</span>
                        </label>
                        <Input.Password
                          prefix={<LockOutlined />}
                          placeholder="At least 8 characters"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                        />
                        {strength && (
                          <div className={styles.strengthRow}>
                            <div className={styles.passwordStrength}>
                              <div className={`${styles.strengthBar} ${styles[strength]}`} />
                              <div className={`${styles.strengthBar} ${strength !== 'weak' ? styles[strength] : ''}`} />
                              <div className={`${styles.strengthBar} ${strength === 'good' ? styles[strength] : ''}`} />
                            </div>
                            <span className={`${styles.strengthLabel} ${styles[strength]}`}>
                              {strength === 'weak' && 'Weak'}
                              {strength === 'fair' && 'Fair'}
                              {strength === 'good' && 'Strong'}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>
                          Confirm <span className={styles.required}>*</span>
                        </label>
                        <Input.Password
                          prefix={<LockOutlined />}
                          placeholder="Re-enter password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          status={!passwordsMatch ? 'error' : undefined}
                        />
                        {!passwordsMatch && (
                          <span className={styles.hint} style={{ color: 'var(--novem-error)' }}>
                            Passwords do not match
                          </span>
                        )}
                      </div>
                    </div>

                    <div className={styles.row}>
                      <div className={styles.field}>
                        <label className={styles.label}>Security question</label>
                        <Select
                          value={securityQuestion}
                          onChange={setSecurityQuestion}
                          options={SECURITY_QUESTIONS.map((q) => ({ value: q, label: q }))}
                          style={{ width: '100%' }}
                          suffixIcon={<QuestionCircleOutlined />}
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Answer</label>
                        <Input
                          prefix={<QuestionCircleOutlined />}
                          placeholder="For password recovery"
                          value={securityAnswer}
                          onChange={(e) => setSecurityAnswer(e.target.value)}
                        />
                      </div>
                    </div>
                    <span className={styles.hint}>Optional — enables password recovery if you forget it</span>
                  </div>

                  {error && <p className={styles.error}>{error}</p>}

                  <div className={styles.actions}>
                    <Button
                      type="primary"
                      size="large"
                      onClick={handleNext}
                      disabled={!isProfileValid}
                      icon={<ArrowRightOutlined />}
                      iconPlacement="end"
                    >
                      Next — Preferences
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Step 1: Preferences */}
            {step === 1 && (
              <div className={styles.stepContent}>
                <h2 className={styles.stepTitle}>Set your preferences</h2>
                <p className={styles.stepDesc}>Configure regional and display settings.</p>

                <div className={styles.form}>
                  <div className={styles.fieldGroup}>
                    <span className={styles.groupLabel}><GlobalOutlined /> Location</span>
                    <div className={styles.row}>
                      <div className={styles.field}>
                        <label className={styles.label}>Region</label>
                        <Select
                          value={region}
                          onChange={setRegion}
                          options={REGIONS}
                          style={{ width: '100%' }}
                          showSearch
                          optionFilterProp="label"
                          suffixIcon={<GlobalOutlined />}
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Timezone</label>
                        <Select
                          value={timezone}
                          onChange={setTimezone}
                          options={TIMEZONES}
                          style={{ width: '100%' }}
                          showSearch
                          optionFilterProp="label"
                        />
                      </div>
                    </div>
                  </div>

                  <div className={styles.fieldGroup}>
                    <span className={styles.groupLabel}><AppstoreOutlined /> Display</span>
                    <div className={styles.row}>
                      <div className={styles.field}>
                        <label className={styles.label}>Date format</label>
                        <Select
                          value={dateFormat}
                          onChange={setDateFormat}
                          options={DATE_FORMATS}
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Fiscal year start</label>
                        <Select
                          value={fiscalYearStart}
                          onChange={setFiscalYearStart}
                          options={FISCAL_MONTHS}
                          style={{ width: '100%' }}
                          showSearch
                          optionFilterProp="label"
                        />
                      </div>
                    </div>
                  </div>

                  <div className={styles.actionsRow}>
                    <Button size="large" onClick={handleBack} icon={<ArrowLeftOutlined />}>
                      Back
                    </Button>
                    <Button
                      type="primary"
                      size="large"
                      onClick={handleNext}
                      icon={<ArrowRightOutlined />}
                      iconPlacement="end"
                    >
                      Next — Store Setup
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Store */}
            {step === 2 && (
              <div className={styles.stepContent}>
                <h2 className={styles.stepTitle}>Set up your first store</h2>
                <p className={styles.stepDesc}>
                  Create your first e-commerce store to start importing data.
                </p>

                <div className={styles.form}>
                  <div className={styles.field}>
                    <label className={styles.label}>
                      Store name <span className={styles.required}>*</span>
                    </label>
                    <Input
                      size="large"
                      prefix={<ShopOutlined />}
                      placeholder="e.g. My Shopify Store"
                      value={storeName}
                      onChange={(e) => setStoreName(e.target.value)}
                      autoFocus
                    />
                  </div>

                  <div className={styles.fieldGroup}>
                    <span className={styles.groupLabel}><AppstoreOutlined /> Configuration</span>
                    <div className={styles.triCol}>
                      <div className={styles.field}>
                        <label className={styles.label}>Platform</label>
                        <Select
                          value={platform}
                          onChange={setPlatform}
                          options={PLATFORMS}
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Industry</label>
                        <Select
                          value={industry}
                          onChange={setIndustry}
                          options={INDUSTRIES}
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div className={styles.field}>
                        <label className={styles.label}>Currency</label>
                        <Select
                          value={currency}
                          onChange={setCurrency}
                          options={CURRENCIES}
                          style={{ width: '80%' }}
                          showSearch
                          optionFilterProp="label"
                        />
                      </div>
                    </div>
                  </div>

                  <div className={styles.storePreview}>
                    <ShopOutlined className={styles.previewIcon} />
                    <div className={styles.previewText}>
                      <strong>{storeName || 'Your Store'}</strong>
                      <span>{PLATFORMS.find((p) => p.value === platform)?.label} · {INDUSTRIES.find((i) => i.value === industry)?.label} · {currency}</span>
                    </div>
                  </div>

                  <div className={styles.actionsRow}>
                    <Button size="large" onClick={handleBack} icon={<ArrowLeftOutlined />}>
                      Back
                    </Button>
                    <Button
                      type="primary"
                      size="large"
                      onClick={handleNext}
                      disabled={!isStoreValid}
                      icon={<ArrowRightOutlined />}
                      iconPlacement="end"
                    >
                      Next — Review
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Ready */}
            {step === 3 && (
              <div className={styles.stepContent}>
                <h2 className={styles.stepTitle}>You&apos;re all set!</h2>
                <p className={styles.stepDesc}>Review your setup and launch NOVEM.</p>

                <div className={styles.form}>
                  <div className={styles.summaryCard}>
                    <div className={styles.summarySection}>
                      <div className={styles.summarySectionInner}>
                        <UserOutlined className={styles.summaryIcon} />
                        <div className={styles.summarySectionContent}>
                          <span className={styles.summaryLabel}>Profile</span>
                          <span className={styles.summaryValue}>{name}</span>
                          {email && <span className={styles.summaryMeta}>{email}</span>}
                        </div>
                      </div>
                    </div>
                    <div className={styles.summarySection}>
                      <div className={styles.summarySectionInner}>
                        <GlobalOutlined className={styles.summaryIcon} />
                        <div className={styles.summarySectionContent}>
                          <span className={styles.summaryLabel}>Region &amp; Preferences</span>
                          <span className={styles.summaryValue}>{REGIONS.find((r) => r.value === region)?.label} · {timezone}</span>
                          <span className={styles.summaryMeta}>{dateFormat} · Fiscal: {FISCAL_MONTHS.find((m) => m.value === fiscalYearStart)?.label}</span>
                        </div>
                      </div>
                    </div>
                    <div className={styles.summarySection}>
                      <div className={styles.summarySectionInner}>
                        <ShopOutlined className={styles.summaryIcon} />
                        <div className={styles.summarySectionContent}>
                          <span className={styles.summaryLabel}>Store</span>
                          <span className={styles.summaryValue}>{storeName}</span>
                          <span className={styles.summaryMeta}>{PLATFORMS.find((p) => p.value === platform)?.label} · {INDUSTRIES.find((i) => i.value === industry)?.label} · {currency}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {error && <p className={styles.error}>{error}</p>}

                  <div className={styles.actionsRow}>
                    <Button size="large" onClick={handleBack} icon={<ArrowLeftOutlined />}>
                      Back
                    </Button>
                    <Button
                      type="primary"
                      size="large"
                      onClick={handleSubmit}
                      loading={loading || submitting}
                      icon={<RocketOutlined />}
                      iconPlacement="end"
                    >
                      Launch NOVEM
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <p className={styles.footer}>
              All your data stays on this device. Nothing is sent to the cloud.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
