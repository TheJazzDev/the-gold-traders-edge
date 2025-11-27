import type { MarketData, Candle, TimeFrame } from "@/types";

const FINNHUB_BASE_URL = "https://finnhub.io/api/v1";

interface FinnhubQuote {
  c: number;  // Current price
  d: number;  // Change
  dp: number; // Percent change
  h: number;  // High
  l: number;  // Low
  o: number;  // Open
  pc: number; // Previous close
  t: number;  // Timestamp
}

interface FinnhubCandle {
  c: number[]; // Close prices
  h: number[]; // High prices
  l: number[]; // Low prices
  o: number[]; // Open prices
  t: number[]; // Timestamps
  v: number[]; // Volume
  s: string;   // Status
}

function getApiKey(): string {
  return process.env.NEXT_PUBLIC_MARKET_API_KEY || "";
}

export async function fetchCurrentPrice(): Promise<MarketData | null> {
  const apiKey = getApiKey();
  if (!apiKey) {
    console.warn("No API key configured, using simulated data");
    return generateSimulatedPrice();
  }

  try {
    const response = await fetch(
      `${FINNHUB_BASE_URL}/quote?symbol=OANDA:XAU_USD&token=${apiKey}`
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data: FinnhubQuote = await response.json();

    return {
      symbol: "XAUUSD",
      price: data.c,
      open: data.o,
      high: data.h,
      low: data.l,
      close: data.c,
      previousClose: data.pc,
      change: data.d,
      changePercent: data.dp,
      timestamp: data.t * 1000,
    };
  } catch (error) {
    console.error("Failed to fetch price:", error);
    return generateSimulatedPrice();
  }
}

export async function fetchCandleData(
  timeframe: TimeFrame,
  from?: number,
  to?: number
): Promise<Candle[]> {
  const apiKey = getApiKey();
  const now = Math.floor(Date.now() / 1000);
  const toTime = to || now;
  
  const resolutionMap: Record<TimeFrame, string> = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1d": "D",
    "1w": "W",
  };

  const periodMap: Record<TimeFrame, number> = {
    "1m": 60 * 60 * 24,
    "5m": 60 * 60 * 24 * 3,
    "15m": 60 * 60 * 24 * 7,
    "1h": 60 * 60 * 24 * 30,
    "4h": 60 * 60 * 24 * 90,
    "1d": 60 * 60 * 24 * 365,
    "1w": 60 * 60 * 24 * 365 * 2,
  };

  const fromTime = from || toTime - periodMap[timeframe];

  if (!apiKey) {
    return generateSimulatedCandles(timeframe, 200);
  }

  try {
    const response = await fetch(
      `${FINNHUB_BASE_URL}/forex/candle?symbol=OANDA:XAU_USD&resolution=${resolutionMap[timeframe]}&from=${fromTime}&to=${toTime}&token=${apiKey}`
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data: FinnhubCandle = await response.json();

    if (data.s !== "ok" || !data.c) {
      return generateSimulatedCandles(timeframe, 200);
    }

    return data.c.map((_, i) => ({
      time: data.t[i],
      open: data.o[i],
      high: data.h[i],
      low: data.l[i],
      close: data.c[i],
      volume: data.v?.[i],
    }));
  } catch (error) {
    console.error("Failed to fetch candles:", error);
    return generateSimulatedCandles(timeframe, 200);
  }
}

let simulatedPrice = 2650 + Math.random() * 50;

function generateSimulatedPrice(): MarketData {
  const change = (Math.random() - 0.5) * 2;
  simulatedPrice += change;

  const open = simulatedPrice - (Math.random() - 0.5) * 5;
  const high = Math.max(simulatedPrice, open) + Math.random() * 3;
  const low = Math.min(simulatedPrice, open) - Math.random() * 3;

  return {
    symbol: "XAUUSD",
    price: simulatedPrice,
    open,
    high,
    low,
    close: simulatedPrice,
    previousClose: simulatedPrice - change,
    change,
    changePercent: (change / simulatedPrice) * 100,
    timestamp: Date.now(),
  };
}

function generateSimulatedCandles(timeframe: TimeFrame, count: number): Candle[] {
  const candles: Candle[] = [];
  const now = Math.floor(Date.now() / 1000);

  const intervalMap: Record<TimeFrame, number> = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
  };

  const interval = intervalMap[timeframe];
  let price = 2600 + Math.random() * 100;

  for (let i = count - 1; i >= 0; i--) {
    const time = now - i * interval;
    const volatility = 5 + Math.random() * 10;
    const trend = Math.sin(i / 20) * 0.3;
    const change = (Math.random() - 0.5 + trend) * volatility;

    const open = price;
    price += change;
    const close = price;
    const high = Math.max(open, close) + Math.random() * volatility * 0.5;
    const low = Math.min(open, close) - Math.random() * volatility * 0.5;

    candles.push({
      time,
      open,
      high,
      low,
      close,
      volume: Math.floor(Math.random() * 10000),
    });
  }

  return candles;
}

export class PriceStream {
  private intervalId: NodeJS.Timeout | null = null;
  private callbacks: Set<(price: MarketData) => void> = new Set();

  subscribe(callback: (price: MarketData) => void) {
    this.callbacks.add(callback);

    if (!this.intervalId) {
      this.start();
    }

    return () => {
      this.callbacks.delete(callback);
      if (this.callbacks.size === 0) {
        this.stop();
      }
    };
  }

  private async start() {
    const fetchAndBroadcast = async () => {
      const price = await fetchCurrentPrice();
      if (price) {
        this.callbacks.forEach((cb) => cb(price));
      }
    };

    await fetchAndBroadcast();
    this.intervalId = setInterval(fetchAndBroadcast, 5000);
  }

  private stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

export const priceStream = new PriceStream();
