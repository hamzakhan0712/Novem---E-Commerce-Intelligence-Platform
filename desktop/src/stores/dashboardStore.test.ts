import { describe, it, expect, beforeEach } from 'vitest';
import { useDashboardStore } from '@/stores/dashboardStore';

describe('dashboardStore', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      period: '30d',
      metric: 'revenue',
      granularity: 'daily',
      kpis: null,
      trends: [],
      revenueAtRisk: null,
      loading: false,
      error: null,
    });
  });

  it('has correct default state', () => {
    const state = useDashboardStore.getState();
    expect(state.period).toBe('30d');
    expect(state.metric).toBe('revenue');
    expect(state.granularity).toBe('daily');
    expect(state.kpis).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setPeriod updates period', () => {
    useDashboardStore.getState().setPeriod('7d');
    expect(useDashboardStore.getState().period).toBe('7d');
  });

  it('setMetric updates metric', () => {
    useDashboardStore.getState().setMetric('orders');
    expect(useDashboardStore.getState().metric).toBe('orders');
  });

  it('setGranularity updates granularity', () => {
    useDashboardStore.getState().setGranularity('weekly');
    expect(useDashboardStore.getState().granularity).toBe('weekly');
  });
});
