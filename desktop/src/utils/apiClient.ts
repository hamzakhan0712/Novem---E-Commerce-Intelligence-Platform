import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

import type { ApiResponse } from '@/types/api';

const ENGINE_BASE_URL = import.meta.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:44945';

const MAX_RETRIES = 2;
const RETRY_DELAYS = [1000, 3000];

interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
}

const apiClient = axios.create({
  baseURL: ENGINE_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function shouldRetry(error: AxiosError): boolean {
  const config = error.config as RetryConfig | undefined;
  if (!config || config.method !== 'get') return false;
  const count = config._retryCount ?? 0;
  if (count >= MAX_RETRIES) return false;
  if (!error.response) return true;
  return error.response.status === 503;
}

apiClient.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse | undefined;
    if (body && body.success === false && body.error) {
      console.error(`[API] ${body.error.code}: ${body.error.detail}`);
    }
    return response;
  },
  async (error: AxiosError) => {
    if (shouldRetry(error)) {
      const config = error.config as RetryConfig;
      config._retryCount = (config._retryCount ?? 0) + 1;
      const delay = RETRY_DELAYS[config._retryCount - 1] ?? RETRY_DELAYS[RETRY_DELAYS.length - 1];
      await new Promise((resolve) => setTimeout(resolve, delay));
      return apiClient(config);
    }

    // On 401, clear auth state (session expired or invalid)
    if (error.response?.status === 401) {
      const url = error.config?.url ?? '';
      if (!url.startsWith('/auth/')) {
        localStorage.removeItem('novem-session-token');
        delete apiClient.defaults.headers.common['Authorization'];
      }
    }

    if (axios.isAxiosError(error)) {
      const responseData = error.response?.data as Record<string, unknown> | undefined;
      const errorObj = responseData?.error as Record<string, unknown> | undefined;
      const detail = (errorObj?.detail as string) ?? error.message;
      const code = (errorObj?.code as string) ?? error.code ?? 'NETWORK_ERROR';
      const apiError = new Error(detail) as Error & { code: string; apiResponse: ApiResponse };
      apiError.code = code;
      apiError.apiResponse = {
        success: false,
        data: null,
        error: { code, detail },
      };
      return Promise.reject(apiError);
    }
    return Promise.reject(error);
  },
);

export default apiClient;
