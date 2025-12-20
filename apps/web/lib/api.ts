import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for backtest operations
});

// Types
export interface PerformanceSummary {
  total_signals: number;
  winning_signals: number;
  losing_signals: number;
  total_pnl: number;
  total_return_pct: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  initial_balance: number;
  final_balance: number;
}

export interface RulePerformance {
  name: string;
  total_signals: number;
  winning_signals: number;
  losing_signals: number;
  win_rate: number;
  net_pnl: number;
  avg_pnl: number;
  profit_factor: number;
}

export interface TradeDetail {
  id: number;
  signal_name: string;
  direction: 'long' | 'short';
  entry_time: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number | null;
  exit_time: string | null;
  exit_price: number | null;
  pnl: number;
  pnl_pct: number;
  status: string;
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
  count: number;
}

// API Functions
export async function getPerformanceSummary(
  timeframe: string,
  rules: string
): Promise<PerformanceSummary> {
  const response = await api.get('/v1/analytics/summary', {
    params: { timeframe, rules },
  });
  return response.data;
}

export async function getRulePerformance(
  timeframe: string,
  rules: string
): Promise<RulePerformance[]> {
  const response = await api.get('/v1/analytics/by-rule', {
    params: { timeframe, rules },
  });
  return response.data;
}

export async function getTradeHistory(
  timeframe: string,
  rules: string
): Promise<TradeDetail[]> {
  const response = await api.get('/v1/analytics/trades', {
    params: { timeframe, rules },
  });
  return response.data;
}

export async function getOHLCV(
  timeframe: string,
  limit: number = 500
): Promise<OHLCVResponse> {
  const response = await api.get('/v1/market/ohlcv', {
    params: { timeframe, limit },
  });
  return response.data;
}

export async function getLatestSignals(timeframe: string, rules?: string) {
  const response = await api.get('/v1/signals/latest', {
    params: { timeframe, rules },
  });
  return response.data;
}

export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}

// Combined backtest result type
export interface CombinedBacktestResult {
  summary: PerformanceSummary;
  rules: RulePerformance[];
  trades: TradeDetail[];
}

// Run backtest once and get all results
export async function runBacktest(
  timeframe: string,
  rules: string
): Promise<CombinedBacktestResult> {
  const response = await api.get('/v1/analytics/backtest', {
    params: { timeframe, rules },
  });
  return response.data;
}
