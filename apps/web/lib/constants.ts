// Trading Rules Configuration
// Using descriptive names instead of Rule 1, 2, etc.

export interface TradingRule {
  id: string;
  name: string;
  description: string;
  performance: string;
  isProfitable: boolean;
  isNew?: boolean;
}

export const ALL_RULES: TradingRule[] = [
  // Original profitable rules
  {
    id: 'golden_retracement',
    name: 'Golden Retracement (61.8%)',
    description: 'Price retraces to the golden ratio Fibonacci level',
    performance: '44% return, 52.6% win rate',
    isProfitable: true,
  },
  {
    id: 'ath_breakout_retest',
    name: 'ATH Breakout Retest',
    description: 'Retest of all-time high as support after breakout',
    performance: '30% return, 38% win rate',
    isProfitable: true,
  },
  {
    id: 'momentum_50',
    name: '50% Momentum',
    description: 'Equilibrium entry in strong momentum at 50% retracement',
    performance: '293% return, 76% win rate ⭐',
    isProfitable: true,
  },
  // New rules
  {
    id: 'rsi_divergence',
    name: 'RSI Divergence',
    description: 'Bullish/bearish divergence between price and RSI indicator',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
  {
    id: 'ema_crossover',
    name: 'EMA Crossover (9/21)',
    description: 'Fast EMA crosses slow EMA with trend confirmation',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
  {
    id: 'london_breakout',
    name: 'London Session Breakout',
    description: 'Breakout of Asian session range during London open',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
  {
    id: 'order_block',
    name: 'Order Block Retest',
    description: 'Smart money concept - institutional entry zone retest',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
  {
    id: 'vwap_deviation',
    name: 'VWAP Deviation',
    description: 'Mean reversion when price deviates 2+ ATR from VWAP',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
  {
    id: 'bollinger_squeeze',
    name: 'Bollinger Band Squeeze',
    description: 'Low volatility squeeze followed by explosive breakout',
    performance: 'Backtesting...',
    isProfitable: true,
    isNew: true,
  },
];

// IDs of profitable rules (for quick selection)
export const PROFITABLE_RULES = [
  'golden_retracement',
  'ath_breakout_retest',
  'momentum_50',
];

// All available timeframes
export const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
];
