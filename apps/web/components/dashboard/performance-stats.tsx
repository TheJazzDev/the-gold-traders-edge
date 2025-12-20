'use client';

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatPercent, formatNumber } from "@/lib/utils";
import { TrendingUp, TrendingDown, Target, BarChart3, DollarSign, Award } from "lucide-react";
import type { PerformanceSummary } from "@/lib/api";

interface PerformanceStatsProps {
  data: PerformanceSummary;
  loading?: boolean;
}

export function PerformanceStats({ data, loading }: PerformanceStatsProps) {
  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white/5 rounded-xl p-6 animate-pulse">
            <div className="h-4 w-20 bg-white/10 rounded mb-4"></div>
            <div className="h-8 w-24 bg-white/10 rounded mb-2"></div>
            <div className="h-3 w-16 bg-white/10 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    {
      title: "Total Return",
      value: formatPercent(data.total_return_pct),
      change: data.total_return_pct > 0 ? "+" + formatPercent(data.total_return_pct) : formatPercent(data.total_return_pct),
      changeType: data.total_return_pct > 0 ? "positive" : "negative",
      icon: data.total_return_pct > 0 ? TrendingUp : TrendingDown,
      description: `${data.total_signals} total signals`,
      gradient: data.total_return_pct > 0 ? "from-green-500/20 to-emerald-500/10" : "from-red-500/20 to-rose-500/10",
      iconBg: data.total_return_pct > 0 ? "bg-green-500/30" : "bg-red-500/30",
      iconColor: data.total_return_pct > 0 ? "text-green-400" : "text-red-400",
    },
    {
      title: "Win Rate",
      value: formatPercent(data.win_rate),
      change: `${data.winning_signals}/${data.total_signals}`,
      changeType: data.win_rate > 50 ? "positive" : "negative",
      icon: Target,
      description: "Winning trades",
      gradient: data.win_rate > 50 ? "from-blue-500/20 to-cyan-500/10" : "from-orange-500/20 to-amber-500/10",
      iconBg: "bg-blue-500/30",
      iconColor: "text-blue-400",
    },
    {
      title: "Profit Factor",
      value: formatNumber(data.profit_factor),
      change: data.profit_factor > 1.5 ? "Excellent" : data.profit_factor > 1 ? "Good" : "Poor",
      changeType: data.profit_factor > 1.5 ? "positive" : data.profit_factor > 1 ? "neutral" : "negative",
      icon: BarChart3,
      description: "Risk/Reward ratio",
      gradient: "from-purple-500/20 to-violet-500/10",
      iconBg: "bg-purple-500/30",
      iconColor: "text-purple-400",
    },
    {
      title: "Sharpe Ratio",
      value: formatNumber(data.sharpe_ratio),
      change: data.sharpe_ratio > 3 ? "Exceptional" : data.sharpe_ratio > 2 ? "Excellent" : "Good",
      changeType: data.sharpe_ratio > 3 ? "positive" : "neutral",
      icon: Award,
      description: "Risk-adjusted return",
      gradient: "from-amber-500/20 to-yellow-500/10",
      iconBg: "bg-amber-500/30",
      iconColor: "text-amber-400",
    },
    {
      title: "Avg Win",
      value: formatCurrency(data.avg_win),
      change: formatCurrency(data.avg_win),
      changeType: "positive",
      icon: DollarSign,
      description: "Per winning trade",
      gradient: "from-emerald-500/20 to-teal-500/10",
      iconBg: "bg-emerald-500/30",
      iconColor: "text-emerald-400",
    },
    {
      title: "Max Drawdown",
      value: formatPercent(data.max_drawdown_pct),
      change: data.max_drawdown_pct < 15 ? "Low Risk" : data.max_drawdown_pct < 25 ? "Moderate" : "High Risk",
      changeType: data.max_drawdown_pct < 15 ? "positive" : data.max_drawdown_pct < 25 ? "neutral" : "negative",
      icon: TrendingDown,
      description: "Maximum loss",
      gradient: data.max_drawdown_pct < 15 ? "from-green-500/20 to-emerald-500/10" : "from-red-500/20 to-rose-500/10",
      iconBg: data.max_drawdown_pct < 15 ? "bg-green-500/30" : "bg-red-500/30",
      iconColor: data.max_drawdown_pct < 15 ? "text-green-400" : "text-red-400",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat, index) => {
        const Icon = stat.icon;

        return (
          <div
            key={stat.title}
            className={`relative overflow-hidden bg-gradient-to-br ${stat.gradient} backdrop-blur-sm rounded-xl border border-white/10 p-6 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl`}
            style={{ animationDelay: `${index * 100}ms` }}
          >
            {/* Decorative gradient orb */}
            <div className="absolute -top-10 -right-10 w-24 h-24 bg-white/5 rounded-full blur-2xl"></div>

            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white/70">
                {stat.title}
              </h3>
              <div className={`p-2.5 rounded-xl ${stat.iconBg}`}>
                <Icon className={`h-5 w-5 ${stat.iconColor}`} />
              </div>
            </div>

            <div className="text-3xl font-bold text-white mb-2">{stat.value}</div>

            <div className="flex items-center justify-between">
              <p className={`text-sm font-semibold ${
                stat.changeType === 'positive' ? 'text-green-400' :
                stat.changeType === 'negative' ? 'text-red-400' :
                'text-white/60'
              }`}>
                {stat.change}
              </p>
              <p className="text-xs text-white/50 font-medium">{stat.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
