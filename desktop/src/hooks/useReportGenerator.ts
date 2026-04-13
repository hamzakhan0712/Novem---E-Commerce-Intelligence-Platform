import { useState, useCallback } from 'react';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

type ReportMode = 'technical' | 'ceo';
type ReportPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';

interface ReportGeneratorState {
  generating: boolean;
  error: string | null;
  lastFilename: string | null;
}

export function useReportGenerator() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const [state, setState] = useState<ReportGeneratorState>({
    generating: false,
    error: null,
    lastFilename: null,
  });

  const generate = useCallback(async (period: ReportPeriod, mode: ReportMode) => {
    if (!activeStoreId) {
      setState((s) => ({ ...s, error: 'No store selected' }));
      return;
    }

    setState({ generating: true, error: null, lastFilename: null });

    try {
      const response = await apiClient.post(
        '/export/narrative-report',
        { store_id: activeStoreId, period, mode },
        { responseType: 'blob', timeout: 120000 },
      );

      const disposition = response.headers['content-disposition'] ?? '';
      const match = disposition.match(/filename="?([^";\n]+)"?/);
      const filename = match?.[1] ?? `novem_report_${mode}_${period}.pdf`;

      const blob = new Blob([response.data as BlobPart], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      setState({ generating: false, error: null, lastFilename: filename });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Report generation failed';
      setState({ generating: false, error: message, lastFilename: null });
    }
  }, [activeStoreId]);

  return {
    ...state,
    hasStore: Boolean(activeStoreId),
    generate,
  };
}
