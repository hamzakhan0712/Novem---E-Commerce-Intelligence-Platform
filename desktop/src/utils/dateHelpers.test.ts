import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatDate, relativeTime } from '@/utils/dateHelpers';

describe('formatDate', () => {
  it('formats date as YYYY-MM-DD by default', () => {
    expect(formatDate('2024-03-15T10:00:00Z')).toBe('2024-03-15');
  });

  it('formats as MM/DD/YYYY', () => {
    expect(formatDate('2024-03-15T10:00:00Z', 'MM/DD/YYYY')).toBe('03/15/2024');
  });

  it('formats as DD/MM/YYYY', () => {
    expect(formatDate('2024-03-15T10:00:00Z', 'DD/MM/YYYY')).toBe('15/03/2024');
  });

  it('accepts Date objects', () => {
    const d = new Date(2024, 0, 5); // Jan 5
    expect(formatDate(d)).toBe('2024-01-05');
  });
});

describe('relativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "just now" for very recent dates', () => {
    const recent = new Date('2024-06-15T11:59:50Z');
    expect(relativeTime(recent)).toBe('just now');
  });

  it('returns minutes ago', () => {
    const fiveMinAgo = new Date('2024-06-15T11:55:00Z');
    expect(relativeTime(fiveMinAgo)).toBe('5m ago');
  });

  it('returns hours ago', () => {
    const threeHrAgo = new Date('2024-06-15T09:00:00Z');
    expect(relativeTime(threeHrAgo)).toBe('3h ago');
  });

  it('returns days ago', () => {
    const fiveDaysAgo = new Date('2024-06-10T12:00:00Z');
    expect(relativeTime(fiveDaysAgo)).toBe('5d ago');
  });

  it('returns formatted date for >30 days', () => {
    const old = new Date('2024-01-01T12:00:00Z');
    expect(relativeTime(old)).toBe('2024-01-01');
  });
});
