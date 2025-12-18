'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Scatter } from 'recharts';
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
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Price Chart with Signals</CardTitle>
          <CardDescription>Candlestick chart showing entry points, stop-loss, and take-profit levels</CardDescription>
        </CardHeader>
        <CardContent className="h-96 animate-pulse bg-gray-100 rounded"></CardContent>
      </Card>
    );
  }

  if (candles.length === 0) {
    return (
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Price Chart with Signals</CardTitle>
          <CardDescription>Candlestick chart showing entry points, stop-loss, and take-profit levels</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-gray-500 py-8">No price data available</p>
        </CardContent>
      </Card>
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
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Price Chart with Signals</CardTitle>
        <CardDescription>Candlestick chart showing entry points, stop-loss, and take-profit levels</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={500}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis
              dataKey="timestamp"
              className="text-xs"
              tick={{ fill: '#374151' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              className="text-xs"
              domain={['dataMin - 50', 'dataMax + 50']}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
              tick={{ fill: '#374151' }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-4 rounded-lg shadow-lg border">
                      <p className="font-semibold mb-2 text-gray-900">{data.timestamp}</p>
                      <div className="space-y-1 text-sm">
                        <p className="text-gray-700">
                          <span className="font-medium">Open:</span> {formatCurrency(data.open)}
                        </p>
                        <p className="text-gray-700">
                          <span className="font-medium">High:</span> {formatCurrency(data.high)}
                        </p>
                        <p className="text-gray-700">
                          <span className="font-medium">Low:</span> {formatCurrency(data.low)}
                        </p>
                        <p className="text-gray-700">
                          <span className="font-medium">Close:</span> {formatCurrency(data.close)}
                        </p>
                        {data.trades && data.trades.length > 0 && (
                          <>
                            <hr className="my-2" />
                            <p className="font-semibold text-blue-600">
                              {data.trades.length} Signal{data.trades.length > 1 ? 's' : ''}:
                            </p>
                            {data.trades.map((trade: TradeDetail, i: number) => (
                              <div key={i} className="text-xs space-y-1 mt-1">
                                <p className="text-gray-900 font-medium">{trade.signal_name}</p>
                                <p className="text-gray-700">
                                  Entry: {formatCurrency(trade.entry_price)} |
                                  SL: {formatCurrency(trade.stop_loss)} |
                                  TP: {trade.take_profit ? formatCurrency(trade.take_profit) : 'N/A'}
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
              fill="#d1d5db"
              stroke="#9ca3af"
              strokeWidth={1}
            />

            {/* Price line */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="#3b82f6"
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

        <div className="mt-4 flex items-center gap-6 text-xs text-gray-700">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span>Close Price</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[8px] border-b-green-500"></div>
            <span>Long Entry</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[8px] border-b-red-500"></div>
            <span>Short Entry</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
