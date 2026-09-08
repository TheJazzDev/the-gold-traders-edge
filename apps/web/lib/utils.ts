import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

/** R-multiples (pnl_pips / risk_pips) are how edge is measured — there's no
 * real dollar account behind these signals yet. */
export function formatR(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}R`;
}

export function formatProfitFactor(value: number | null): string {
  return value === null ? '—' : value.toFixed(2);
}

/** API datetimes (e.g. "2026-09-04T13:00:00") are naive-UTC, no offset —
 * `new Date(...)` on a string like that is parsed as browser-local time,
 * silently mislabeling every timestamp for any viewer not in UTC (this bit
 * the Telegram bot the same way before it normalized at the source; see
 * YahooFinanceDataFeed.get_latest_candles()). Force UTC parsing instead. */
export function parseApiDate(value: string): Date {
  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
