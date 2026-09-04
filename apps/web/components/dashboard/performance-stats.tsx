"use client";

import { Target, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import type { PerformanceStats as PerformanceStatsType } from "@/lib/types";
import { formatR, formatProfitFactor } from "@/lib/utils";

interface PerformanceStatsProps {
  data: PerformanceStatsType;
  loading?: boolean;
}

export function PerformanceStats({ data, loading }: PerformanceStatsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="glass rounded-xl p-4 sm:p-6 animate-pulse">
            <div className="h-4 w-20 bg-white/10 rounded mb-4" />
            <div className="h-8 w-24 bg-white/10 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const positive = data.net_r_multiple >= 0;
  const stats = [
    {
      title: "Win Rate",
      value: `${data.win_rate.toFixed(1)}%`,
      description: `${data.win_count}W / ${data.loss_count}L`,
      icon: Target,
      tone: data.win_rate >= 50 ? "positive" : data.total_closed > 0 ? "negative" : "neutral",
    },
    {
      title: "Net R-Multiple",
      value: formatR(data.net_r_multiple),
      description: `${data.total_closed} resolved signal${data.total_closed === 1 ? "" : "s"}`,
      icon: positive ? TrendingUp : TrendingDown,
      tone: data.total_closed === 0 ? "neutral" : positive ? "positive" : "negative",
    },
    {
      title: "Profit Factor",
      value: formatProfitFactor(data.profit_factor),
      description: data.profit_factor === null ? "No losses yet" : "Gains ÷ losses (R)",
      icon: BarChart3,
      tone:
        data.profit_factor === null
          ? "neutral"
          : data.profit_factor >= 1
            ? "positive"
            : "negative",
    },
    {
      title: "Total Signals",
      value: String(data.total_signals),
      description: `${data.total_signals - data.total_closed} still open`,
      icon: Target,
      tone: "neutral" as const,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        const toneColor =
          stat.tone === "positive"
            ? "text-green-400"
            : stat.tone === "negative"
              ? "text-red-400"
              : "text-muted-foreground";
        return (
          <div key={stat.title} className="glass rounded-xl p-4 sm:p-6">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
              <h3 className="text-xs sm:text-sm font-semibold text-white/70">{stat.title}</h3>
              <Icon className={`h-4 w-4 sm:h-5 sm:w-5 ${toneColor}`} />
            </div>
            <div className={`text-2xl sm:text-3xl font-bold ${toneColor}`}>{stat.value}</div>
            <p className="text-xs text-white/50 mt-1 sm:mt-2">{stat.description}</p>
          </div>
        );
      })}
    </div>
  );
}
