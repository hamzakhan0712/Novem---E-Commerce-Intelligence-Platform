import { useState } from 'react';

import { Menu } from 'antd';
import {
  SettingOutlined,
  LockOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

import ProfileSettings from '@/components/settings/ProfileSettings';
import GeneralSettings from '@/components/settings/GeneralSettings';
import SecuritySettings from '@/components/settings/SecuritySettings';
import SystemSettings from '@/components/settings/SystemSettings';

import styles from './Settings.module.css';

const SECTIONS = [
  { key: 'general', label: 'General', icon: <SettingOutlined /> },
  { key: 'security', label: 'Security', icon: <LockOutlined /> },
  { key: 'system', label: 'System', icon: <InfoCircleOutlined /> },
];

export default function Settings() {
  const [activeSection, setActiveSection] = useState('general');

  return (
    <div className={styles.settingsLayout}>
      <div className={styles.sidebar}>
        <div className={styles.sidebarTitle}>Settings</div>
        <Menu
          mode="vertical"
          selectedKeys={[activeSection]}
          onClick={({ key }) => setActiveSection(key)}
          items={SECTIONS}
          className={styles.sidebarMenu}
        />
      </div>
      <div className={styles.content}>
        <div className={styles.contentInner}>
          {activeSection === 'general' && (
            <>
              <ProfileSettings />
              <GeneralSettings />
            </>
          )}
          {activeSection === 'security' && <SecuritySettings />}
          {activeSection === 'system' && <SystemSettings />}
        </div>
      </div>
    </div>
  );
}
