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

// ALL 5 PROFITABLE RULES - Always active, matches backend exactly
export const ALL_RULES: TradingRule[] = [
  {
    id: 'momentum_equilibrium',
    name: 'Momentum Equilibrium',
    description: 'Equilibrium entry in strong momentum at 50% retracement',
    performance: '76% WR, 293% return ⭐',
    isProfitable: true,
  },
  {
    id: 'london_session_breakout',
    name: 'London Session Breakout',
    description: 'Breakout of Asian session range during London open',
    performance: '58.8% WR, 2.74 PF',
    isProfitable: true,
  },
  {
    id: 'golden_fibonacci',
    name: 'Golden Fibonacci (61.8%)',
    description: 'Price retraces to the golden ratio Fibonacci level',
    performance: '52.6% WR, 44% return',
    isProfitable: true,
  },
  {
    id: 'ath_retest',
    name: 'ATH Breakout Retest',
    description: 'Retest of all-time high as support after breakout',
    performance: '38% WR, 30% return',
    isProfitable: true,
  },
  {
    id: 'order_block_retest',
    name: 'Order Block Retest',
    description: 'Smart money concept - institutional entry zone retest',
    performance: 'Institutional zones',
    isProfitable: true,
  },
];

// All rules are profitable and always enabled
export const PROFITABLE_RULES = ALL_RULES.map(r => r.id);

// All 6 active timeframes - matches backend exactly
export const TIMEFRAMES = [
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
];
