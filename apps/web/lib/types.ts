/**
 * Shared API response types.
 *
 * There is no real dollar account behind these signals yet, so performance
 * is measured in R-multiples (pnl_pips / risk_pips) rather than dollar P&L
 * — see packages/engine/src/database/signal_repository.py.
 */

export type SignalDirection = "LONG" | "SHORT";
export type SignalStatus =
  | "pending"
  | "active"
  | "closed_tp"
  | "closed_sl"
  | "closed_manual"
  | "cancelled";

export interface Signal {
  id: number;
  timestamp: string;
  symbol: string;
  timeframe: string;
  strategy_name: string;
  direction: SignalDirection;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  risk_pips: number;
  reward_pips: number;
  risk_reward_ratio: number;
  status: SignalStatus;
  pnl: number | null;
  pnl_pct: number | null;
}

export interface SignalsResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export interface PerformanceStats {
  total_signals: number;
  total_closed: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  avg_r_multiple: number;
  net_r_multiple: number;
  /** null = undefined (no losses yet), not 0 */
  profit_factor: number | null;
  largest_win_r: number;
  largest_loss_r: number;
}

export interface RulePerformance {
  strategy_name: string;
  total_signals: number;
  closed_signals: number;
  wins: number;
  losses: number;
  win_rate: number;
  net_r_multiple: number;
  avg_r_multiple: number;
  profit_factor: number | null;
}

export interface Trade {
  id: number;
  signal_name: string;
  direction: SignalDirection;
  entry_time: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  exit_time: string | null;
  exit_price: number | null;
  r_multiple: number;
  status: SignalStatus;
  risk_reward: number | null;
}

/** One trading rule with its live enabled state and real validated
 * performance on the running timeframe — see GET /v1/settings/strategies. */
export interface StrategyPerformance {
  key: string;
  name: string;
  enabled: boolean;
  timeframe: string;
  validated: boolean;
  profit_factor: number | null;
  win_rate: number | null;
  total_trades: number | null;
  net_profit_pct: number | null;
}

export interface Setting {
  id: number;
  key: string;
  category: string;
  value: string;
  value_type: "string" | "int" | "float" | "bool" | "json";
  typed_value: unknown;
  default_value: string;
  description: string | null;
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  editable: boolean;
  requires_restart: boolean;
  last_modified_by: string | null;
  updated_at: string | null;
}

export type SettingsByCategory = Record<string, Setting[]>;

export interface ServiceStatus {
  status: string;
  service_status: string;
  auto_trading_enabled: boolean;
  dry_run_mode: boolean;
  max_risk_per_trade: number;
  max_positions: number;
  enabled_timeframes: string[];
  enabled_strategies: string[];
  data_feed_type: string;
  active_timeframes: string[];
}

export interface MarketStatus {
  is_open: boolean;
  reason: string;
  current_time: string;
  timezone: string;
  next_open: string | null;
  next_close: string | null;
  time_until_event: string | null;
  market_hours: { description: string; open: string; close: string };
}
