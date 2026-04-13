import { BgColorsOutlined, LoadingOutlined, ZoomInOutlined, ZoomOutOutlined } from '@ant-design/icons';

import { useAppStore } from '@/stores/appStore';
import { useStoreStore } from '@/stores/storeStore';

import styles from './StatusBar.module.css';

export default function StatusBar() {
  const engineStatus = useAppStore((s) => s.engineStatus);
  const themeMode = useAppStore((s) => s.themeMode);
  const toggleTheme = useAppStore((s) => s.toggleThemeMode);
  const zoomLevel = useAppStore((s) => s.zoomLevel);
  const zoomIn = useAppStore((s) => s.zoomIn);
  const zoomOut = useAppStore((s) => s.zoomOut);
  const backgroundTasks = useAppStore((s) => s.backgroundTasks);
  const activeStore = useStoreStore((s) => s.stores.find((st) => st.id === s.activeStoreId));

  return (
    <footer className={styles.statusBar}>
      <span id="tour-engine-status" className={styles.statusItem}>
        <span
          className={`${styles.dot} ${engineStatus === 'connected' ? styles.dotGreen : engineStatus === 'connecting' ? styles.dotYellow : styles.dotRed}`}
        />
        {engineStatus === 'connected' ? 'Engine Working' : engineStatus === 'connecting' ? 'Starting…' : 'Offline'}
      </span>

      {backgroundTasks.length > 0 && (
        <span className={styles.statusItem} title={backgroundTasks.map((t) => `${t.label}: ${t.progress}%`).join(', ')}>
          <LoadingOutlined spin style={{ fontSize: 11, marginRight: 4 }} />
          {backgroundTasks[0].label} {backgroundTasks[0].progress}%
          {backgroundTasks.length > 1 && ` (+${backgroundTasks.length - 1})`}
        </span>
      )}

      {activeStore && (
        <span id="tour-store-name" className={styles.statusItem}>
          <span className={styles.separator}>·</span>
          <span className={styles.storeName}>{activeStore.name}</span>
        </span>
      )}

      <div className={styles.spacer} />

      <span className={styles.versionBadge}>v0.3.0</span>

      <span id="tour-zoom-controls" className={styles.statusItem}>
        <ZoomOutOutlined
          className={styles.zoomBtn}
          onClick={zoomOut}
          title="Zoom out"
        />
        <span title="Zoom level">{zoomLevel}%</span>
        <ZoomInOutlined
          className={styles.zoomBtn}
          onClick={zoomIn}
          title="Zoom in"
        />
      </span>

      <span
        id="tour-theme-toggle"
        className={`${styles.statusItem} ${styles.clickable}`}
        onClick={toggleTheme}
        title="Toggle theme"
      >
        <BgColorsOutlined style={{ fontSize: 12 }} />
        {themeMode === 'dark' ? 'Dark' : 'Light'}
      </span>
    </footer>
  );
}
