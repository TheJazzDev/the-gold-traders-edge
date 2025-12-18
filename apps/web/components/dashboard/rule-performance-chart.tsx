'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { RulePerformance } from "@/lib/api";

interface RulePerformanceChartProps {
  data: RulePerformance[];
  loading?: boolean;
}

export function RulePerformanceChart({ data, loading }: RulePerformanceChartProps) {
  if (loading) {
    return (
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Rule Performance</CardTitle>
          <CardDescription>Performance breakdown by trading rule</CardDescription>
        </CardHeader>
        <CardContent className="h-80 animate-pulse bg-gray-100 rounded"></CardContent>
      </Card>
    );
  }

  const chartData = data.map((rule) => ({
    name: rule.name,
    'Net P&L': rule.net_pnl,
    'Win Rate': rule.win_rate,
    'Profit Factor': rule.profit_factor,
    winRate: rule.win_rate,
    trades: rule.total_signals,
  }));

  const getBarColor = (pnl: number) => {
    return pnl >= 0 ? '#10b981' : '#ef4444';
  };

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Rule Performance</CardTitle>
        <CardDescription>Net P&L by trading rule</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis
              dataKey="name"
              className="text-xs"
              angle={-45}
              textAnchor="end"
              height={100}
              tick={{ fill: '#374151' }}
            />
            <YAxis
              className="text-xs"
              tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
              tick={{ fill: '#374151' }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-4 rounded-lg shadow-lg border">
                      <p className="font-semibold mb-2">{data.name}</p>
                      <p className="text-sm">
                        <span className="font-medium">Net P&L:</span>{' '}
                        <span className={data['Net P&L'] >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {formatCurrency(data['Net P&L'])}
                        </span>
                      </p>
                      <p className="text-sm">
                        <span className="font-medium">Win Rate:</span> {formatPercent(data.winRate)}
                      </p>
                      <p className="text-sm">
                        <span className="font-medium">Trades:</span> {data.trades}
                      </p>
                      <p className="text-sm">
                        <span className="font-medium">Profit Factor:</span> {data['Profit Factor'].toFixed(2)}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="Net P&L" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry['Net P&L'])} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
