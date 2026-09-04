"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { RulePerformance } from "@/lib/types";
import { formatProfitFactor } from "@/lib/utils";

interface RulePerformanceChartProps {
  data: RulePerformance[];
  loading?: boolean;
}

export function RulePerformanceChart({ data, loading }: RulePerformanceChartProps) {
  if (loading) {
    return <div className="h-64 sm:h-80 glass rounded-xl animate-pulse" />;
  }

  if (data.length === 0) {
    return (
      <div className="glass rounded-xl p-6 sm:p-8 text-center text-sm text-white/50">
        No resolved signals yet — this fills in once trades close.
      </div>
    );
  }

  const chartData = data.map((rule) => ({
    name: rule.strategy_name,
    netR: rule.net_r_multiple,
    winRate: rule.win_rate,
    profitFactor: rule.profit_factor,
    trades: rule.total_signals,
  }));

  return (
    <div className="glass rounded-xl p-4 sm:p-6">
      <div className="mb-4 sm:mb-6">
        <h3 className="text-base sm:text-xl font-bold text-white">Net R-Multiple by Rule</h3>
        <p className="text-xs sm:text-sm text-white/60 mt-1">Which strategies are actually earning their keep</p>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="name"
            angle={-30}
            textAnchor="end"
            height={70}
            interval={0}
            tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.2)" }}
          />
          <YAxis
            tickFormatter={(value) => `${value}R`}
            tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.2)" }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div className="bg-slate-900/95 backdrop-blur-sm p-3 rounded-lg shadow-xl border border-white/10 text-xs">
                  <p className="font-bold text-white mb-1">{d.name}</p>
                  <p className="text-white/80">
                    Net: <span className={d.netR >= 0 ? "text-green-400" : "text-red-400"}>{d.netR.toFixed(2)}R</span>
                  </p>
                  <p className="text-white/80">Win rate: {d.winRate.toFixed(1)}%</p>
                  <p className="text-white/80">Profit factor: {formatProfitFactor(d.profitFactor)}</p>
                  <p className="text-white/80">Trades: {d.trades}</p>
                </div>
              );
            }}
          />
          <Bar dataKey="netR" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.netR >= 0 ? "#10b981" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
