import type {
  Candle,
  TechnicalAnalysis,
  PatternDetection,
  IndicatorValues,
  Signal,
  SignalDirection,
} from "@/types";
import { generateId } from "@/lib/utils";

export function calculateRSI(closes: number[], period: number = 14): number {
  if (closes.length < period + 1) return 50;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) {
      gains += change;
    } else {
      losses -= change;
    }
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) {
      avgGain = (avgGain * (period - 1) + change) / period;
      avgLoss = (avgLoss * (period - 1)) / period;
    } else {
      avgGain = (avgGain * (period - 1)) / period;
      avgLoss = (avgLoss * (period - 1) - change) / period;
    }
  }

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function calculateEMA(data: number[], period: number): number[] {
  const ema: number[] = [];
  const multiplier = 2 / (period + 1);

  ema[0] = data[0];

  for (let i = 1; i < data.length; i++) {
    ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1];
  }

  return ema;
}

export function calculateMACD(closes: number[]): {
  value: number;
  signal: number;
  histogram: number;
} {
  if (closes.length < 26) {
    return { value: 0, signal: 0, histogram: 0 };
  }

  const ema12 = calculateEMA(closes, 12);
  const ema26 = calculateEMA(closes, 26);

  const macdLine = ema12.map((v, i) => v - ema26[i]);
  const signalLine = calculateEMA(macdLine.slice(-9), 9);

  const value = macdLine[macdLine.length - 1];
  const signal = signalLine[signalLine.length - 1];

  return {
    value,
    signal,
    histogram: value - signal,
  };
}

export function calculateATR(candles: Candle[], period: number = 14): number {
  if (candles.length < period + 1) return 0;

  const trueRanges: number[] = [];

  for (let i = 1; i < candles.length; i++) {
    const high = candles[i].high;
    const low = candles[i].low;
    const prevClose = candles[i - 1].close;

    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low - prevClose)
    );
    trueRanges.push(tr);
  }

  const atr =
    trueRanges.slice(-period).reduce((sum, tr) => sum + tr, 0) / period;
  return atr;
}

export function calculateBollingerBands(
  closes: number[],
  period: number = 20,
  stdDev: number = 2
): { upper: number; middle: number; lower: number } {
  if (closes.length < period) {
    const mid = closes[closes.length - 1] || 0;
    return { upper: mid, middle: mid, lower: mid };
  }

  const slice = closes.slice(-period);
  const sma = slice.reduce((sum, v) => sum + v, 0) / period;

  const squaredDiffs = slice.map((v) => Math.pow(v - sma, 2));
  const variance = squaredDiffs.reduce((sum, v) => sum + v, 0) / period;
  const std = Math.sqrt(variance);

  return {
    upper: sma + stdDev * std,
    middle: sma,
    lower: sma - stdDev * std,
  };
}

export function findSupportResistance(candles: Candle[]): {
  support: number[];
  resistance: number[];
} {
  const pivotPoints: { price: number; type: "high" | "low" }[] = [];
  const lookback = 5;

  for (let i = lookback; i < candles.length - lookback; i++) {
    const current = candles[i];
    let isHigh = true;
    let isLow = true;

    for (let j = i - lookback; j <= i + lookback; j++) {
      if (j === i) continue;
      if (candles[j].high >= current.high) isHigh = false;
      if (candles[j].low <= current.low) isLow = false;
    }

    if (isHigh) pivotPoints.push({ price: current.high, type: "high" });
    if (isLow) pivotPoints.push({ price: current.low, type: "low" });
  }

  const clusterThreshold = calculateATR(candles) * 0.5 || 10;
  const clusters: { price: number; count: number; type: "high" | "low" }[] = [];

  for (const pivot of pivotPoints) {
    const existing = clusters.find(
      (c) => Math.abs(c.price - pivot.price) < clusterThreshold
    );
    if (existing) {
      existing.price = (existing.price + pivot.price) / 2;
      existing.count++;
    } else {
      clusters.push({ ...pivot, count: 1 });
    }
  }

  const significant = clusters
    .filter((c) => c.count >= 2)
    .sort((a, b) => b.count - a.count);

  return {
    support: significant
      .filter((c) => c.type === "low")
      .slice(0, 3)
      .map((c) => c.price),
    resistance: significant
      .filter((c) => c.type === "high")
      .slice(0, 3)
      .map((c) => c.price),
  };
}

export function detectPatterns(candles: Candle[]): PatternDetection[] {
  const patterns: PatternDetection[] = [];
  const len = candles.length;
  if (len < 20) return patterns;

  const recent = candles.slice(-20);
  const highs = recent.map((c) => c.high);
  const lows = recent.map((c) => c.low);
  const closes = recent.map((c) => c.close);

  const highSlope = (highs[highs.length - 1] - highs[0]) / highs.length;
  const lowSlope = (lows[lows.length - 1] - lows[0]) / lows.length;

  if (highSlope < -0.5 && lowSlope > 0.5) {
    patterns.push({
      name: "Symmetrical Triangle",
      type: "continuation",
      direction: closes[closes.length - 1] > closes[0] ? "bullish" : "bearish",
      confidence: 0.7,
    });
  }

  if (Math.abs(highSlope) < 0.2 && lowSlope > 0.5) {
    patterns.push({
      name: "Ascending Triangle",
      type: "continuation",
      direction: "bullish",
      confidence: 0.75,
    });
  }

  if (highSlope < -0.5 && Math.abs(lowSlope) < 0.2) {
    patterns.push({
      name: "Descending Triangle",
      type: "continuation",
      direction: "bearish",
      confidence: 0.75,
    });
  }

  const last3 = candles.slice(-3);
  if (
    last3[2].close > last3[2].open &&
    last3[1].close < last3[1].open &&
    last3[0].close < last3[0].open &&
    last3[2].close > last3[1].high
  ) {
    patterns.push({
      name: "Bullish Engulfing",
      type: "reversal",
      direction: "bullish",
      confidence: 0.65,
    });
  }

  return patterns;
}

export function analyzeTechnicals(candles: Candle[]): TechnicalAnalysis {
  const closes = candles.map((c) => c.close);
  const currentPrice = closes[closes.length - 1];

  const ema20 = calculateEMA(closes, 20);
  const ema50 = calculateEMA(closes, 50);
  const ema200 = calculateEMA(closes, 200);

  const ema20Val = ema20[ema20.length - 1];
  const ema50Val = ema50[ema50.length - 1] || ema20Val;
  const ema200Val = ema200[ema200.length - 1] || ema50Val;

  let trend: "BULLISH" | "BEARISH" | "NEUTRAL" = "NEUTRAL";
  let strength = 50;

  if (currentPrice > ema20Val && ema20Val > ema50Val) {
    trend = "BULLISH";
    strength = 70;
    if (ema50Val > ema200Val) strength = 85;
  } else if (currentPrice < ema20Val && ema20Val < ema50Val) {
    trend = "BEARISH";
    strength = 70;
    if (ema50Val < ema200Val) strength = 85;
  }

  const rsi = calculateRSI(closes);
  const macd = calculateMACD(closes);
  const atr = calculateATR(candles);
  const bb = calculateBollingerBands(closes);
  const levels = findSupportResistance(candles);
  const patterns = detectPatterns(candles);

  if (rsi > 70) strength = Math.min(strength + 10, 95);
  if (rsi < 30) strength = Math.min(strength + 10, 95);
  if (macd.histogram > 0 && trend === "BULLISH") strength += 5;
  if (macd.histogram < 0 && trend === "BEARISH") strength += 5;

  return {
    trend,
    strength: Math.min(strength, 100),
    support: levels.support,
    resistance: levels.resistance,
    patterns,
    indicators: {
      rsi,
      macd,
      ema: {
        ema20: ema20Val,
        ema50: ema50Val,
        ema200: ema200Val,
      },
      atr,
      bollingerBands: bb,
    },
  };
}

export function generateSignal(
  candles: Candle[],
  analysis: TechnicalAnalysis
): Signal | null {
  const currentPrice = candles[candles.length - 1].close;
  const { trend, strength, support, resistance, patterns, indicators } = analysis;

  if (strength < 65) return null;

  const hasConfluence = patterns.length > 0 || 
    (indicators.rsi < 35 && trend === "BULLISH") ||
    (indicators.rsi > 65 && trend === "BEARISH");

  if (!hasConfluence) return null;

  const atr = indicators.atr;
  let direction: SignalDirection;
  let entryLow: number;
  let entryHigh: number;
  let stopLoss: number;
  let tp1: number;
  let tp2: number;

  if (trend === "BULLISH") {
    direction = "BUY";
    entryLow = currentPrice - atr * 0.2;
    entryHigh = currentPrice + atr * 0.3;
    stopLoss = Math.max(support[0] || currentPrice - atr * 2, currentPrice - atr * 1.5);
    tp1 = currentPrice + atr * 1.5;
    tp2 = resistance[0] || currentPrice + atr * 3;
  } else if (trend === "BEARISH") {
    direction = "SELL";
    entryLow = currentPrice - atr * 0.3;
    entryHigh = currentPrice + atr * 0.2;
    stopLoss = Math.min(resistance[0] || currentPrice + atr * 2, currentPrice + atr * 1.5);
    tp1 = currentPrice - atr * 1.5;
    tp2 = support[0] || currentPrice - atr * 3;
  } else {
    return null;
  }

  const risk = Math.abs(currentPrice - stopLoss);
  const reward = Math.abs(tp1 - currentPrice);
  const rr = risk > 0 ? reward / risk : 0;

  if (rr < 1.5) return null;

  const confidenceScore = Math.min(
    (strength / 100) * 0.4 +
      (patterns.length > 0 ? 0.2 : 0) +
      (rr >= 2 ? 0.2 : rr >= 1.5 ? 0.1 : 0) +
      (hasConfluence ? 0.2 : 0),
    0.95
  );

  return {
    id: generateId(),
    createdAt: new Date(),
    updatedAt: new Date(),
    direction,
    status: "PENDING",
    entryZone: { low: entryLow, high: entryHigh },
    stopLoss,
    takeProfit1: tp1,
    takeProfit2: tp2,
    riskRewardRatio: rr,
    confidenceScore,
    timeframe: "1h",
    analysis: `${trend} trend detected with ${strength}% strength. ${patterns.map((p) => p.name).join(", ") || "Price action"} suggests ${direction.toLowerCase()} opportunity.`,
    patterns: patterns.map((p) => p.name),
  };
}
