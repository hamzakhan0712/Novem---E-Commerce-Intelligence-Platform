import { useEffect, useRef, useCallback } from 'react';

import apiClient from '@/utils/apiClient';
import { useAppStore } from '@/stores/appStore';
import type { ApiResponse, HealthResponse } from '@/types/api';

const FAST_INTERVAL = 3_000;
const SLOW_INTERVAL = 60_000;

export function useEngineHealth() {
  const setEngineStatus = useAppStore((s) => s.setEngineStatus);
  const engineStatus = useAppStore((s) => s.engineStatus);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusRef = useRef(engineStatus);
  statusRef.current = engineStatus;

  const scheduleNext = useCallback(() => {
    const delay = statusRef.current === 'connected' ? SLOW_INTERVAL : FAST_INTERVAL;
    timerRef.current = setTimeout(runCheck, delay);
  }, []);

  const runCheck = useCallback(async () => {
    try {
      const res = await apiClient.get<ApiResponse<HealthResponse>>('/health');
      if (res.data.success && res.data.data?.status === 'ok') {
        setEngineStatus('connected');
      } else {
        setEngineStatus('disconnected');
      }
    } catch {
      setEngineStatus('disconnected');
    }
    scheduleNext();
  }, [setEngineStatus, scheduleNext]);

  useEffect(() => {
    runCheck();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [runCheck]);

  return engineStatus;
}
