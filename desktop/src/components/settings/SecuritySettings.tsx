import { useState } from 'react';

import { Input, Button, Select, Switch, message } from 'antd';
import { LockOutlined } from '@ant-design/icons';

import { useAuthStore } from '@/stores/authStore';
import { useSettingsStore } from '@/stores/settingsStore';

import styles from './GeneralSettings.module.css';

const PASSWORD_POLICY_OPTIONS = [
  { value: 'every_start', label: 'Every app start' },
  { value: 'once_per_session', label: 'Once per session' },
  { value: 'never', label: 'Never (auto-login)' },
];

export default function SecuritySettings() {
  const { loading, error, changePassword, clearError, setPasswordPolicy } = useAuthStore();
  const passwordPolicy = useSettingsStore((s) => s.passwordPolicy);
  const piiMaskingEnabled = useSettingsStore((s) => s.piiMaskingEnabled);
  const updateSetting = useSettingsStore((s) => s.updateSetting);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNew, setConfirmNew] = useState('');

  const passwordValid =
    currentPassword.length > 0 &&
    newPassword.length >= 4 &&
    newPassword === confirmNew;

  const handleChangePassword = async () => {
    if (!passwordValid) return;
    await changePassword(currentPassword, newPassword);
    if (!error) {
      message.success('Password changed');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNew('');
    }
  };

  return (
    <div>
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Change Password</div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Current password</span>
          </div>
          <div className={styles.formControl} style={{ width: 240 }}>
            <Input.Password
              value={currentPassword}
              onChange={(e) => {
                setCurrentPassword(e.target.value);
                if (error) clearError();
              }}
              prefix={<LockOutlined />}
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>New password</span>
          </div>
          <div className={styles.formControl} style={{ width: 240 }}>
            <Input.Password
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 4 characters"
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Confirm new password</span>
          </div>
          <div className={styles.formControl} style={{ width: 240 }}>
            <Input.Password
              value={confirmNew}
              onChange={(e) => setConfirmNew(e.target.value)}
              status={confirmNew && newPassword !== confirmNew ? 'error' : undefined}
            />
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <Button
            icon={<LockOutlined />}
            onClick={handleChangePassword}
            loading={loading}
            disabled={!passwordValid}
          >
            Change Password
          </Button>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Password Policy</div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Require password</span>
            <span className={styles.labelHint}>When NOVEM should ask you to unlock</span>
          </div>
          <div className={styles.formControl}>
            <Select
              value={passwordPolicy}
              onChange={(val) => {
                updateSetting('password_policy', val);
                setPasswordPolicy(val);
              }}
              style={{ width: 180 }}
              options={PASSWORD_POLICY_OPTIONS}
            />
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Privacy</div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Protect Customer Privacy</span>
            <span className={styles.labelHint}>Automatically hide personal details like emails and names when importing</span>
          </div>
          <div className={styles.formControl}>
            <Switch
              checked={piiMaskingEnabled}
              onChange={(val) => updateSetting('piiMaskingEnabled', val)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
