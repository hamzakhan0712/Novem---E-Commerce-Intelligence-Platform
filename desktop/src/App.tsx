import { Suspense, lazy, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp, Spin, theme } from 'antd';

import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useStoreStore } from '@/stores/storeStore';
import { useDataAvailabilityStore } from '@/stores/dataAvailabilityStore';
import { useSyncStore } from '@/stores/syncStore';
import { ROUTES } from '@/constants/routes';
import { NOVEM_ACCENT } from '@/constants/theme';

import { PageErrorBoundary } from '@/components/shared/PageErrorBoundary';
import { AppErrorBoundary } from '@/components/shared/AppErrorBoundary';
import AppShell from '@/components/shell/AppShell';

import Landing from '@/pages/Landing';
import Welcome from '@/pages/Welcome';
import Login from '@/pages/Login';
import StoreSwitcher from '@/pages/StoreSwitcher';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Customers = lazy(() => import('@/pages/Customers'));
const Products = lazy(() => import('@/pages/Products'));
const Insights = lazy(() => import('@/pages/Insights'));
const Forecasting = lazy(() => import('@/pages/Forecasting'));
const Sentiment = lazy(() => import('@/pages/Sentiment'));
const Copilot = lazy(() => import('@/pages/Copilot'));
const ImportData = lazy(() => import('@/pages/ImportData'));
const DataViewer = lazy(() => import('@/pages/DataViewer'));
const Stores = lazy(() => import('@/pages/Stores'));
const Marketing = lazy(() => import('@/pages/Marketing'));
const Reports = lazy(() => import('@/pages/Reports'));
const Settings = lazy(() => import('@/pages/Settings'));

const PageFallback = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 300 }}>
    <Spin size="large" />
  </div>
);

const SEEN_LANDING_KEY = 'novem-seen-landing';

function AuthGate() {
  const { isSetupComplete, isAuthenticated, isLocked, passwordPolicy, checkStatus, autoLogin } = useAuthStore();
  const fetchSettings = useSettingsStore((s) => s.fetchSettings);
  const stores = useStoreStore((s) => s.stores);
  const storesLoading = useStoreStore((s) => s.loading);
  const fetchStores = useStoreStore((s) => s.fetchStores);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const fetchTableCounts = useDataAvailabilityStore((s) => s.fetchTableCounts);
  const resetAvailability = useDataAvailabilityStore((s) => s.reset);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Auto-login when password policy is 'never', user isn't authenticated, and app wasn't explicitly locked
  useEffect(() => {
    if (isSetupComplete && !isAuthenticated && !isLocked && passwordPolicy === 'never') {
      autoLogin();
    }
  }, [isSetupComplete, isAuthenticated, isLocked, passwordPolicy, autoLogin]);

  useEffect(() => {
    if (isSetupComplete && isAuthenticated) {
      fetchSettings();
      fetchStores();
    }
  }, [isSetupComplete, isAuthenticated, fetchSettings, fetchStores]);

  useEffect(() => {
    if (isAuthenticated && activeStoreId) {
      fetchTableCounts(activeStoreId);
    } else if (!activeStoreId) {
      resetAvailability();
    }
  }, [isAuthenticated, activeStoreId, lastSyncTick, fetchTableCounts, resetAvailability]);

  // Still loading initial status
  if (isSetupComplete === null) {
    return null;
  }

  if (!isSetupComplete) {
    const hasSeenLanding = localStorage.getItem(SEEN_LANDING_KEY) === 'true';
    return (
      <Routes>
        <Route path={ROUTES.LANDING} element={<Landing />} />
        <Route path={ROUTES.WELCOME} element={<Welcome />} />
        <Route path="*" element={<Navigate to={hasSeenLanding ? ROUTES.WELCOME : ROUTES.LANDING} replace />} />
      </Routes>
    );
  }

  if (!isAuthenticated) {
    // For 'never' policy, auto-login is in progress — don't flash Login screen
    if (passwordPolicy === 'never' && !isLocked) {
      return null;
    }
    return (
      <Routes>
        <Route path={ROUTES.LOGIN} element={<Login />} />
        <Route path="*" element={<Navigate to={ROUTES.LOGIN} replace />} />
      </Routes>
    );
  }

  // Store switcher when multiple stores exist (user hasn't chosen yet this session)
  const showStoreSwitcher = !storesLoading && stores.length >= 2;

  return (
    <Routes>
      {showStoreSwitcher && (
        <Route path={ROUTES.STORE_SWITCHER} element={<StoreSwitcher />} />
      )}
      <Route element={<AppShell />}>
        <Route path={ROUTES.SPLASH} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
        <Route path={ROUTES.DASHBOARD} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Dashboard /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.CUSTOMERS} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Customers /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.PRODUCTS} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Products /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.MARKETING} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Marketing /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.INSIGHTS} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Insights /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.FORECASTING} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Forecasting /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.SENTIMENT} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Sentiment /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.COPILOT} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Copilot /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.IMPORT} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><ImportData /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.DATA_VIEWER} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><DataViewer /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.STORES} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Stores /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.REPORTS} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Reports /></Suspense></PageErrorBoundary>} />
        <Route path={ROUTES.SETTINGS} element={<PageErrorBoundary><Suspense fallback={<PageFallback />}><Settings /></Suspense></PageErrorBoundary>} />
      </Route>
      <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    </Routes>
  );
}

export default function App() {
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'novem-theme' && (e.newValue === 'dark' || e.newValue === 'light')) {
        setThemeMode(e.newValue);
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [setThemeMode]);

  return (
    <AppErrorBoundary>
      <ConfigProvider
        theme={{
          algorithm: themeMode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: NOVEM_ACCENT,
            fontFamily: "var(--novem-font-family)",
            borderRadius: 6,
          },
        }}
      >
        <AntApp>
          <HashRouter>
            <AuthGate />
          </HashRouter>
        </AntApp>
      </ConfigProvider>
    </AppErrorBoundary>
  );
}
