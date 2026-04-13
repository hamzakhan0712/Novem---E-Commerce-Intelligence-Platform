import { useEffect, useState, useRef } from 'react';

import { SyncOutlined, CheckCircleFilled } from '@ant-design/icons';

import { useSyncStore } from '@/stores/syncStore';
import { useStoreStore } from '@/stores/storeStore';

import styles from './SyncBanner.module.css';

export default function SyncBanner() {
  const isSyncing = useSyncStore((s) => s.isSyncing);
  const syncLabel = useSyncStore((s) => s.syncLabel);
  const syncStartedAt = useSyncStore((s) => s.syncStartedAt);
  const recentActivity = useSyncStore((s) => s.recentActivity);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const fetchActivity = useSyncStore((s) => s.fetchActivity);
  const pollForNewData = useSyncStore((s) => s.pollForNewData);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);

  const [elapsed, setElapsed] = useState(0);
  const [showDone, setShowDone] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevTickRef = useRef(lastSyncTick);

  // Elapsed timer while syncing
  useEffect(() => {
    if (isSyncing && syncStartedAt) {
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - syncStartedAt) / 1000));
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isSyncing, syncStartedAt]);

  // Show "done" banner briefly when sync completes
  useEffect(() => {
    if (lastSyncTick > prevTickRef.current && !isSyncing) {
      setShowDone(true);
      if (activeStoreId) fetchActivity(activeStoreId);
      doneTimerRef.current = setTimeout(() => setShowDone(false), 5000);
    }
    prevTickRef.current = lastSyncTick;
    return () => {
      if (doneTimerRef.current) clearTimeout(doneTimerRef.current);
    };
  }, [lastSyncTick, isSyncing, activeStoreId, fetchActivity]);

  // Fetch initial activity
  useEffect(() => {
    if (activeStoreId) fetchActivity(activeStoreId);
  }, [activeStoreId, fetchActivity]);

  // Lightweight poller — detects new webhook data every 10s
  useEffect(() => {
    if (!activeStoreId) return;
    const id = setInterval(() => pollForNewData(activeStoreId), 10_000);
    return () => clearInterval(id);
  }, [activeStoreId, pollForNewData]);

  const formatElapsed = (s: number) =>
    s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;

  const bannerClass = isSyncing
    ? `${styles.banner} ${styles.bannerSyncing}`
    : showDone
      ? `${styles.banner} ${styles.bannerDone}`
      : `${styles.banner} ${styles.bannerHidden}`;

  return (
    <div className={bannerClass}>
      {isSyncing && (
        <>
          <SyncOutlined spin style={{ fontSize: 14, color: '#1677ff' }} />
          <span className={styles.label}>{syncLabel || 'Syncing data…'}</span>
          <span className={styles.elapsed}>{formatElapsed(elapsed)}</span>
        </>
      )}

      {!isSyncing && showDone && (
        <>
          <CheckCircleFilled style={{ fontSize: 14, color: '#52c41a' }} />
          <span className={styles.label}>Data updated</span>
          {recentActivity.length > 0 && (
            <div className={styles.activityList}>
              {recentActivity.slice(0, 3).map((a) => (
                <span key={a.id} className={styles.activityItem}>
                  <strong>{a.row_count_raw}</strong> {a.data_type} rows
                </span>
              ))}
            </div>
          )}
          <span className={styles.detail}>All pages will refresh automatically</span>
        </>
      )}
    </div>
  );
}
