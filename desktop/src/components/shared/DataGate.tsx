import type { ReactNode } from 'react';

import { Spin } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useStoreStore } from '@/stores/storeStore';
import { useDataAvailabilityStore } from '@/stores/dataAvailabilityStore';
import { EmptyState } from '@/components/shared/EmptyState';
import { ROUTES } from '@/constants/routes';

interface DataGateProps {
  pageKey: string;
  children: ReactNode;
  className?: string;
}

export default function DataGate({ pageKey, children, className }: DataGateProps) {
  const navigate = useNavigate();
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const loading = useDataAvailabilityStore((s) => s.loading);
  const loaded = useDataAvailabilityStore((s) => s.loaded);
  const isPageAccessible = useDataAvailabilityStore((s) => s.isPageAccessible);

  if (!activeStoreId) {
    return (
      <div className={className} style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <EmptyState
          title="No store selected"
          description="Create or select a store to get started."
          action={{ label: 'Go to Stores', onClick: () => navigate(ROUTES.STORES) }}
        />
      </div>
    );
  }

  if (!loaded || loading) {
    return (
      <div className={className} style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 0 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isPageAccessible(pageKey)) {
    return (
      <div className={className} style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <EmptyState
          title="No data available"
          description="Import the required data to unlock this page."
          action={{ label: 'Import Data', onClick: () => navigate(ROUTES.IMPORT) }}
        />
      </div>
    );
  }

  return <>{children}</>;
}
