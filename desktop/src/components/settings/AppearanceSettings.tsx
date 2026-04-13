import { Select, Slider } from 'antd';

import { useSettingsStore } from '@/stores/settingsStore';
import { useAppStore } from '@/stores/appStore';

import styles from './GeneralSettings.module.css';

export default function AppearanceSettings() {
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);
  const zoomLevel = useAppStore((s) => s.zoomLevel);
  const setZoomLevel = useAppStore((s) => s.setZoomLevel);
  const updateSetting = useSettingsStore((s) => s.updateSetting);

  return (
    <div>
      <div className={styles.section}>
        <div className={styles.sectionTitle}>Appearance</div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Theme</span>
            <span className={styles.labelHint}>Switch between dark and light mode</span>
          </div>
          <div className={styles.formControl}>
            <Select
              value={themeMode}
              onChange={(val) => {
                setThemeMode(val);
                updateSetting('theme', val);
              }}
              style={{ width: 120 }}
              options={[
                { value: 'dark', label: 'Dark' },
                { value: 'light', label: 'Light' },
              ]}
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formLabel}>
            <span className={styles.labelText}>Zoom Level</span>
            <span className={styles.labelHint}>{zoomLevel}%</span>
          </div>
          <div className={styles.formControl} style={{ width: 200 }}>
            <Slider
              min={80}
              max={150}
              step={5}
              value={zoomLevel}
              onChange={(val) => {
                setZoomLevel(val);
                updateSetting('zoomLevel', val);
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
