import { useEffect } from 'react';

import { Outlet, useNavigate } from 'react-router-dom';

import { useEngineHealth } from '@/hooks/useEngineHealth';
import { useAppStore } from '@/stores/appStore';
import { ROUTES } from '@/constants/routes';
import CommandPalette from './CommandPalette';
import AppTour from './AppTour';

import TitleBar from './TitleBar';
import ActivityBar from './ActivityBar';
import SyncBanner from './SyncBanner';
import StatusBar from './StatusBar';
import styles from './AppShell.module.css';

export default function AppShell() {
  useEngineHealth();
  const toggleCommandPalette = useAppStore((s) => s.toggleCommandPalette);
  const zoomIn = useAppStore((s) => s.zoomIn);
  const zoomOut = useAppStore((s) => s.zoomOut);
  const resetZoom = useAppStore((s) => s.resetZoom);
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrl = e.ctrlKey || e.metaKey;
      if (!isCtrl) return;

      // Ctrl+, — open settings
      if (e.key === ',') {
        e.preventDefault();
        navigate(ROUTES.SETTINGS);
        return;
      }

      // Ctrl+I — import data
      if (e.key === 'i' || e.key === 'I') {
        e.preventDefault();
        navigate(ROUTES.IMPORT);
        return;
      }

      // Ctrl+K — command palette
      if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        toggleCommandPalette();
        return;
      }

      // Ctrl++ / Ctrl+= — zoom in
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        zoomIn();
        return;
      }

      // Ctrl+- — zoom out
      if (e.key === '-') {
        e.preventDefault();
        zoomOut();
        return;
      }

      // Ctrl+0 — reset zoom
      if (e.key === '0') {
        e.preventDefault();
        resetZoom();
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, toggleCommandPalette, zoomIn, zoomOut, resetZoom]);

  return (
    <div className={styles.shell}>
      <TitleBar />
      <SyncBanner />
      <div className={styles.body}>
        <ActivityBar />
        <main className={styles.main}>
          <div className={styles.content}>
            <Outlet />
          </div>
        </main>
      </div>
      <StatusBar />
      <CommandPalette />
      <AppTour />
    </div>
  );
}
