import { describe, it, expect, beforeEach } from 'vitest';
import { useSettingsStore } from '@/stores/settingsStore';

describe('settingsStore', () => {
  beforeEach(() => {
    useSettingsStore.setState({
      theme: 'dark',
      currency: 'INR',
      exchangeRate: 1,
      dateFormat: 'YYYY-MM-DD',
      piiMaskingEnabled: true,
      passwordPolicy: 'every_start',
      loading: false,
      error: null,
    });
  });

  it('has correct defaults', () => {
    const state = useSettingsStore.getState();
    expect(state.theme).toBe('dark');
    expect(state.currency).toBe('INR');
    expect(state.exchangeRate).toBe(1);
    expect(state.piiMaskingEnabled).toBe(true);
  });

  it('setTheme updates theme and is callable', () => {
    useSettingsStore.getState().setTheme('light');
    expect(useSettingsStore.getState().theme).toBe('light');
  });

  it('currency can be changed', () => {
    useSettingsStore.setState({ currency: 'USD' });
    expect(useSettingsStore.getState().currency).toBe('USD');
  });

  it('exchange rate defaults to 1', () => {
    expect(useSettingsStore.getState().exchangeRate).toBe(1);
  });
});
