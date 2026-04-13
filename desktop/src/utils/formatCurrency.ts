const FORMATTERS = new Map<string, Intl.NumberFormat>();

function getFormatter(currency: string): Intl.NumberFormat {
  if (!FORMATTERS.has(currency)) {
    FORMATTERS.set(
      currency,
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }),
    );
  }
  return FORMATTERS.get(currency)!;
}

let _exchangeRate = 1;
let _activeCurrency = 'INR';

export function setExchangeRate(rate: number, currency: string): void {
  _exchangeRate = rate;
  _activeCurrency = currency;
}

export function getExchangeRate(): number {
  return _exchangeRate;
}

export function getActiveCurrency(): string {
  return _activeCurrency;
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CNY: '¥',
  INR: '₹', KRW: '₩', BRL: 'R$', CAD: 'CA$', AUD: 'A$',
  CHF: 'CHF', SEK: 'kr', NOK: 'kr', DKK: 'kr', PLN: 'zł',
  TRY: '₺', MXN: 'MX$', SGD: 'S$', HKD: 'HK$', NZD: 'NZ$',
  ZAR: 'R', THB: '฿', MYR: 'RM', PHP: '₱',
  AED: 'د.إ', SAR: '﷼', PKR: '₨', BDT: '৳',
};

export function getCurrencySymbol(currency?: string): string {
  const cur = currency ?? _activeCurrency;
  return CURRENCY_SYMBOLS[cur] ?? cur;
}

export function formatCurrency(value: number, currency?: string): string {
  const cur = currency ?? _activeCurrency;
  const v = value ?? 0;
  const converted = cur === 'INR' ? v : v * _exchangeRate;
  return getFormatter(cur).format(converted);
}

export function formatCurrencyCompact(value: number, currency?: string): string {
  const cur = currency ?? _activeCurrency;
  const converted = cur === 'INR' ? value : value * _exchangeRate;
  if (Math.abs(converted) >= 1_000_000) {
    return `${getFormatter(cur).format(Math.round(converted / 1_000_000))}M`;
  }
  if (Math.abs(converted) >= 1_000) {
    return `${getFormatter(cur).format(Math.round(converted / 1_000))}K`;
  }
  return getFormatter(cur).format(converted);
}
