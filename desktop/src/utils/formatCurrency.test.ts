import { describe, it, expect, beforeEach } from 'vitest';
import {
  formatCurrency,
  formatCurrencyCompact,
  setExchangeRate,
  getActiveCurrency,
  getExchangeRate,
} from '@/utils/formatCurrency';

describe('formatCurrency', () => {
  beforeEach(() => {
    setExchangeRate(1, 'INR');
  });

  it('formats INR values correctly', () => {
    const result = formatCurrency(1000);
    expect(result).toContain('1,000');
  });

  it('handles zero', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0');
  });

  it('handles null/undefined gracefully', () => {
    const result = formatCurrency(null as unknown as number);
    expect(result).toContain('0');
  });

  it('respects explicit currency parameter', () => {
    const result = formatCurrency(1000, 'USD');
    expect(result).toContain('$');
  });
});

describe('formatCurrencyCompact', () => {
  beforeEach(() => {
    setExchangeRate(1, 'INR');
  });

  it('formats millions with M suffix', () => {
    const result = formatCurrencyCompact(2_500_000);
    expect(result).toContain('M');
  });

  it('formats thousands with K suffix', () => {
    const result = formatCurrencyCompact(5_000);
    expect(result).toContain('K');
  });

  it('formats small values normally', () => {
    const result = formatCurrencyCompact(500);
    expect(result).not.toContain('K');
    expect(result).not.toContain('M');
  });
});

describe('setExchangeRate / getters', () => {
  it('updates active currency', () => {
    setExchangeRate(0.012, 'USD');
    expect(getActiveCurrency()).toBe('USD');
    expect(getExchangeRate()).toBe(0.012);
  });
});
