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
