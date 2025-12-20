'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { RulePerformance } from "@/lib/api";

interface RulePerformanceChartProps {
  data: RulePerformance[];
  loading?: boolean;
}

export function RulePerformanceChart({ data, loading }: RulePerformanceChartProps) {
  if (loading) {
    return (
      <div className="h-80 bg-white/5 rounded-xl animate-pulse"></div>
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
    <div>
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-2xl">📊</span>
          Rule Performance
        </h3>
        <p className="text-sm text-white/60 mt-1">Net P&L by trading rule</p>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
          />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-slate-800/95 backdrop-blur-sm p-4 rounded-xl shadow-xl border border-white/10">
                    <p className="font-bold text-white mb-2">{data.name}</p>
                    <div className="space-y-1">
                      <p className="text-sm text-white/80">
                        <span className="font-medium">Net P&L:</span>{' '}
                        <span className={data['Net P&L'] >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                          {formatCurrency(data['Net P&L'])}
                        </span>
                      </p>
                      <p className="text-sm text-white/80">
                        <span className="font-medium">Win Rate:</span>{' '}
                        <span className="text-blue-400">{formatPercent(data.winRate)}</span>
                      </p>
                      <p className="text-sm text-white/80">
                        <span className="font-medium">Trades:</span>{' '}
                        <span className="text-amber-400">{data.trades}</span>
                      </p>
                      <p className="text-sm text-white/80">
                        <span className="font-medium">Profit Factor:</span>{' '}
                        <span className="text-purple-400">{data['Profit Factor'].toFixed(2)}</span>
                      </p>
                    </div>
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
    </div>
  );
}
