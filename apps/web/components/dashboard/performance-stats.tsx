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
          <Card key={i} className="animate-pulse bg-slate-800 border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-20 bg-slate-700 rounded"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 w-24 bg-slate-700 rounded mb-2"></div>
              <div className="h-3 w-16 bg-slate-700 rounded"></div>
            </CardContent>
          </Card>
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
    },
    {
      title: "Win Rate",
      value: formatPercent(data.win_rate),
      change: `${data.winning_signals}/${data.total_signals}`,
      changeType: data.win_rate > 50 ? "positive" : "negative",
      icon: Target,
      description: "Winning trades",
    },
    {
      title: "Profit Factor",
      value: formatNumber(data.profit_factor),
      change: data.profit_factor > 1.5 ? "Excellent" : data.profit_factor > 1 ? "Good" : "Poor",
      changeType: data.profit_factor > 1.5 ? "positive" : data.profit_factor > 1 ? "neutral" : "negative",
      icon: BarChart3,
      description: "Risk/Reward ratio",
    },
    {
      title: "Sharpe Ratio",
      value: formatNumber(data.sharpe_ratio),
      change: data.sharpe_ratio > 3 ? "Exceptional" : data.sharpe_ratio > 2 ? "Excellent" : "Good",
      changeType: data.sharpe_ratio > 3 ? "positive" : "neutral",
      icon: Award,
      description: "Risk-adjusted return",
    },
    {
      title: "Avg Win",
      value: formatCurrency(data.avg_win),
      change: formatCurrency(data.avg_win),
      changeType: "positive",
      icon: DollarSign,
      description: "Per winning trade",
    },
    {
      title: "Max Drawdown",
      value: formatPercent(data.max_drawdown_pct),
      change: data.max_drawdown_pct < 15 ? "Low Risk" : data.max_drawdown_pct < 25 ? "Moderate" : "High Risk",
      changeType: data.max_drawdown_pct < 15 ? "positive" : data.max_drawdown_pct < 25 ? "neutral" : "negative",
      icon: TrendingDown,
      description: "Maximum loss",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        const delay = index * 100;

        return (
          <Card
            key={stat.title}
            className="relative overflow-hidden bg-gradient-to-br from-slate-800 to-slate-700 border-slate-600 hover:border-slate-500 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
            style={{ animationDelay: `${delay}ms` }}
          >
            {/* Gradient overlay for positive metrics */}
            {stat.changeType === 'positive' && (
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-500/10 to-transparent rounded-bl-full"></div>
            )}
            {stat.changeType === 'negative' && (
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-red-500/10 to-transparent rounded-bl-full"></div>
            )}

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
              <CardTitle className="text-sm font-semibold text-slate-400">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${
                stat.changeType === 'positive' ? 'bg-green-500/20' :
                stat.changeType === 'negative' ? 'bg-red-500/20' :
                'bg-slate-600'
              }`}>
                <Icon className={`h-4 w-4 ${
                  stat.changeType === 'positive' ? 'text-green-400' :
                  stat.changeType === 'negative' ? 'text-red-400' :
                  'text-slate-400'
                }`} />
              </div>
            </CardHeader>
            <CardContent className="relative z-10">
              <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
              <p className={`text-sm font-semibold mt-1 ${
                stat.changeType === 'positive' ? 'text-green-400' :
                stat.changeType === 'negative' ? 'text-red-400' :
                'text-slate-400'
              }`}>
                {stat.change}
              </p>
              <p className="text-xs text-slate-500 mt-1 font-medium">{stat.description}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
