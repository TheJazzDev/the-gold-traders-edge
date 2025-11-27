export type SignalDirection = "BUY" | "SELL";

export type SignalStatus =
  | "PENDING"
  | "ACTIVE"
  | "TP1_HIT"
  | "TP2_HIT"
  | "SL_HIT"
  | "CANCELLED"
  | "EXPIRED";

export type TimeFrame = "1m" | "5m" | "15m" | "1h" | "4h" | "1d" | "1w";

export interface PriceLevel {
  price: number;
  label: string;
  type: "support" | "resistance" | "entry" | "tp" | "sl";
}

export interface Signal {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  direction: SignalDirection;
  status: SignalStatus;
  entryZone: {
    low: number;
    high: number;
  };
  stopLoss: number;
  takeProfit1: number;
  takeProfit2?: number;
  takeProfit3?: number;
  riskRewardRatio: number;
  confidenceScore: number;
  timeframe: TimeFrame;
  analysis: string;
  patterns: string[];
  triggeredAt?: Date;
  closedAt?: Date;
  closedPrice?: number;
  pnlPips?: number;
  pnlPercent?: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  previousClose: number;
  change: number;
  changePercent: number;
  timestamp: number;
  volume?: number;
}

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface ChartConfig {
  symbol: string;
  timeframe: TimeFrame;
  showVolume: boolean;
  showSignals: boolean;
  showLevels: boolean;
}

export interface TechnicalAnalysis {
  trend: "BULLISH" | "BEARISH" | "NEUTRAL";
  strength: number;
  support: number[];
  resistance: number[];
  patterns: PatternDetection[];
  indicators: IndicatorValues;
}

export interface PatternDetection {
  name: string;
  type: "continuation" | "reversal";
  direction: "bullish" | "bearish";
  confidence: number;
  priceTarget?: number;
}

export interface IndicatorValues {
  rsi: number;
  macd: {
    value: number;
    signal: number;
    histogram: number;
  };
  ema: {
    ema20: number;
    ema50: number;
    ema200: number;
  };
  atr: number;
  bollingerBands: {
    upper: number;
    middle: number;
    lower: number;
  };
}

export interface Notification {
  id: string;
  type: "signal" | "update" | "alert" | "system";
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  signalId?: string;
}

export interface TradeStats {
  totalSignals: number;
  activeSignals: number;
  winRate: number;
  totalPips: number;
  avgRiskReward: number;
  profitFactor: number;
  bestTrade: number;
  worstTrade: number;
  streak: {
    current: number;
    type: "win" | "loss";
  };
}

export interface AppSettings {
  notifications: {
    browser: boolean;
    email: boolean;
    telegram: boolean;
  };
  riskManagement: {
    maxRiskPercent: number;
    minRiskReward: number;
  };
  display: {
    theme: "dark" | "light";
    defaultTimeframe: TimeFrame;
  };
}
