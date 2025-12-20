'use client';

import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Scatter } from 'recharts';
import { formatCurrency } from "@/lib/utils";
import type { Candle, TradeDetail } from "@/lib/api";

interface PriceChartProps {
  candles: Candle[];
  trades: TradeDetail[];
  loading?: boolean;
}

export function PriceChart({ candles, trades, loading }: PriceChartProps) {
  if (loading) {
    return (
      <div className="h-96 bg-white/5 rounded-xl animate-pulse"></div>
    );
  }

  if (candles.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-white/50">No price data available</p>
      </div>
    );
  }

  // Prepare chart data combining candles with trade markers
  const chartData = candles.slice(-200).map((candle, index) => {
    const candleTime = new Date(candle.timestamp).getTime();

    // Find trades that occurred at this candle
    const tradesAtCandle = trades.filter(trade => {
      const entryTime = new Date(trade.entry_time).getTime();
      // Match if within the same candle timeframe (allowing small variance)
      return Math.abs(entryTime - candleTime) < 4 * 60 * 60 * 1000; // 4 hours
    });

    return {
      timestamp: new Date(candle.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      high: candle.high,
      low: candle.low,
      open: candle.open,
      close: candle.close,
      candleBody: [candle.low, candle.high],
      trades: tradesAtCandle,
      // Add entry markers
      entryLong: tradesAtCandle.find(t => t.direction === 'long')?.entry_price,
      entryShort: tradesAtCandle.find(t => t.direction === 'short')?.entry_price,
    };
  });

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-2xl">📈</span>
          Price Chart with Signals
        </h3>
        <p className="text-sm text-white/60 mt-1">Candlestick chart showing entry points, stop-loss, and take-profit levels</p>
      </div>

      <ResponsiveContainer width="100%" height={500}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="timestamp"
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            domain={['dataMin - 50', 'dataMax + 50']}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-slate-800/95 backdrop-blur-sm p-4 rounded-xl shadow-xl border border-white/10">
                    <p className="font-bold text-white mb-3">{data.timestamp}</p>
                    <div className="space-y-1.5 text-sm">
                      <p className="text-white/80">
                        <span className="font-medium text-white/60">Open:</span> <span className="text-white">{formatCurrency(data.open)}</span>
                      </p>
                      <p className="text-white/80">
                        <span className="font-medium text-white/60">High:</span> <span className="text-green-400">{formatCurrency(data.high)}</span>
                      </p>
                      <p className="text-white/80">
                        <span className="font-medium text-white/60">Low:</span> <span className="text-red-400">{formatCurrency(data.low)}</span>
                      </p>
                      <p className="text-white/80">
                        <span className="font-medium text-white/60">Close:</span> <span className="text-amber-400">{formatCurrency(data.close)}</span>
                      </p>
                      {data.trades && data.trades.length > 0 && (
                        <>
                          <hr className="my-2 border-white/10" />
                          <p className="font-bold text-amber-400">
                            {data.trades.length} Signal{data.trades.length > 1 ? 's' : ''}:
                          </p>
                          {data.trades.map((trade: TradeDetail, i: number) => (
                            <div key={i} className="text-xs space-y-1 mt-2 bg-white/5 p-2 rounded-lg">
                              <p className="text-white font-medium">{trade.signal_name}</p>
                              <p className="text-white/70">
                                <span className="text-blue-400">Entry:</span> {formatCurrency(trade.entry_price)} |{' '}
                                <span className="text-red-400">SL:</span> {formatCurrency(trade.stop_loss)} |{' '}
                                <span className="text-green-400">TP:</span> {trade.take_profit ? formatCurrency(trade.take_profit) : 'N/A'}
                              </p>
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />

          {/* Candlestick bodies (high-low range) */}
          <Bar
            dataKey="candleBody"
            fill="rgba(255,255,255,0.1)"
            stroke="rgba(255,255,255,0.3)"
            strokeWidth={1}
          />

          {/* Price line */}
          <Line
            type="monotone"
            dataKey="close"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
          />

          {/* Long entry markers (green) */}
          <Scatter
            dataKey="entryLong"
            fill="#10b981"
            shape="triangle"
          />

          {/* Short entry markers (red) */}
          <Scatter
            dataKey="entryShort"
            fill="#ef4444"
            shape="triangle"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <div className="mt-6 flex items-center justify-center gap-8 text-sm text-white/70">
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-amber-500 rounded-full"></div>
          <span>Close Price</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[10px] border-b-green-500"></div>
          <span>Long Entry</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[10px] border-b-red-500"></div>
          <span>Short Entry</span>
        </div>
      </div>
    </div>
  );
}
