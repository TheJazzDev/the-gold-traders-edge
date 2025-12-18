import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Types
export interface PerformanceSummary {
  period: string;
  timeframe: string;
  total_signals: number;
  winning_signals: number;
  losing_signals: number;
  win_rate: number;
  profit_factor: number;
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  avg_win: number;
  avg_loss: number;
  start_date?: string;
  end_date?: string;
}

export interface RulePerformance {
  name: string;
  total_signals: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  avg_return: number;
}

export interface TradeDetail {
  id: number;
  signal_name: string;
  direction: string;
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number | null;
  stop_loss: number;
  take_profit: number | null;
  status: string;
  pnl: number;
  pnl_pct: number;
  risk_reward: number | null;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVResponse {
  symbol: string;
  timeframe: string;
  candles: Candle[];
}

export interface DateRange {
  startDate: string;
  endDate: string;
}

// API Functions
export async function getPerformanceSummary(
  timeframe: string = '4h',
  rules: string = '1,5,6',
  dateRange?: DateRange
): Promise<PerformanceSummary> {
  const params: Record<string, string> = { timeframe, rules };
  if (dateRange) {
    params.start_date = dateRange.startDate;
    params.end_date = dateRange.endDate;
  }
  const response = await api.get('/v1/analytics/summary', { params });
  return response.data;
}

export async function getRulePerformance(
  timeframe: string = '4h',
  rules: string = '1,5,6',
  dateRange?: DateRange
): Promise<RulePerformance[]> {
  const params: Record<string, string> = { timeframe, rules };
  if (dateRange) {
    params.start_date = dateRange.startDate;
    params.end_date = dateRange.endDate;
  }
  const response = await api.get('/v1/analytics/by-rule', { params });
  return response.data;
}

export async function getTradeHistory(
  timeframe: string = '4h',
  rules: string = '1,5,6',
  dateRange?: DateRange
): Promise<TradeDetail[]> {
  const params: Record<string, string> = { timeframe, rules };
  if (dateRange) {
    params.start_date = dateRange.startDate;
    params.end_date = dateRange.endDate;
  }
  const response = await api.get('/v1/analytics/trades', { params });
  return response.data;
}

export async function getOHLCV(
  timeframe: string = '4h',
  limit: number = 500
): Promise<OHLCVResponse> {
  const response = await api.get('/v1/market/ohlcv', {
    params: { timeframe, limit },
  });
  return response.data;
}

export async function getIndicators(timeframe: string = '4h') {
  const response = await api.get('/v1/market/indicators', {
    params: { timeframe },
  });
  return response.data;
}

// Health check
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch {
    return false;
  }
}
