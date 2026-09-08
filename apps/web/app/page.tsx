"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Zap,
  ArrowUpRight,
  Filter,
  RefreshCw,
  Clock,
  Target,
  Shield,
  Radio,
  BellRing,
  BarChart3,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NavBar } from "@/components/layout/NavBar";
import { MarketStatus } from "@/components/market/MarketStatus";
import { SignalDetailDialog } from "@/components/dashboard/signal-detail-dialog";
import { useSignals } from "@/lib/hooks/useSignals";
import { apiClient } from "@/lib/api/client";
import { formatR, formatProfitFactor } from "@/lib/utils";
import type { PerformanceStats, ServiceStatus, SignalStatus } from "@/lib/types";

const STATUS_FILTERS: { value: SignalStatus | "all"; label: string }[] = [
  { value: "all", label: "All Status" },
  { value: "pending", label: "Pending" },
  { value: "active", label: "Active" },
  { value: "closed_tp", label: "Closed (TP)" },
  { value: "closed_sl", label: "Closed (SL)" },
];

export default function HomePage() {
  const stats = useQuery<PerformanceStats>({
    queryKey: ["performance-stats"],
    queryFn: () => apiClient.getPerformanceStats(),
  });
  const service = useQuery<ServiceStatus>({
    queryKey: ["service-status"],
    queryFn: () => apiClient.getServiceStatus(),
  });

  const [timeframeFilter, setTimeframeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null);
  const { data, isLoading, refetch } = useSignals({
    limit: 50,
    timeframe: timeframeFilter === "all" ? undefined : timeframeFilter,
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  const signals = data?.signals || [];
  const timeframeOptions = ["all", ...(service.data?.active_timeframes || [])];
  const hasResults = (stats.data?.total_closed || 0) > 0;

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-64 h-64 sm:w-96 sm:h-96 bg-amber-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-48 w-64 h-64 sm:w-96 sm:h-96 bg-orange-500/20 rounded-full blur-3xl" />
      </div>

      <NavBar />

      {/* Hero */}
      <section className="relative pt-10 pb-10 sm:pt-16 sm:pb-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs sm:text-sm mb-5 sm:mb-6">
              <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>Live on XAUUSD · {service.data?.active_timeframes?.join(", ").toUpperCase() || "—"}</span>
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 sm:mb-6">
              Professional
              <span className="block mt-1 sm:mt-2 bg-linear-to-r from-amber-400 via-orange-500 to-amber-400 bg-clip-text text-transparent">
                Gold Trading Signals
              </span>
            </h1>

            <p className="text-base sm:text-lg text-gray-400 mb-8 sm:mb-10">
              A live signal service for XAUUSD, posted here and on Telegram the moment a validated setup fires.
              There&apos;s no dollar account behind these signals, so every result below is real and measured in
              R-multiples — not a marketing number.
            </p>
          </div>

          {/* Real stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-4xl mx-auto">
            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-2xl sm:text-3xl font-bold text-amber-400 mb-1 sm:mb-2">
                {hasResults ? `${stats.data!.win_rate.toFixed(0)}%` : "—"}
              </div>
              <div className="text-gray-400 text-sm sm:text-base">Win Rate</div>
              <div className="text-xs text-gray-500 mt-1">
                {hasResults ? `${stats.data!.total_closed} resolved signals` : "No resolved signals yet"}
              </div>
            </Card>
            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-2xl sm:text-3xl font-bold text-amber-400 mb-1 sm:mb-2">
                {hasResults ? formatR(stats.data!.net_r_multiple) : "—"}
              </div>
              <div className="text-gray-400 text-sm sm:text-base">Net R-Multiple</div>
              <div className="text-xs text-gray-500 mt-1">
                Profit factor: {hasResults ? formatProfitFactor(stats.data!.profit_factor) : "—"}
              </div>
            </Card>
            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-2xl sm:text-3xl font-bold text-amber-400 mb-1 sm:mb-2">24/7</div>
              <div className="text-gray-400 text-sm sm:text-base">Live Monitoring</div>
              <div className="text-xs text-gray-500 mt-1">Continuous signal generation</div>
            </Card>
          </div>

          <div className="flex justify-center mt-8 sm:mt-10">
            <Link href="/performance">
              <Button variant="outline" className="border-white/20 text-white hover:bg-white/10">
                See Full Performance Breakdown
                <ArrowUpRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Live signals feed */}
      <section id="signals" className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16">
        <div className="mb-4 sm:mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-1">Live Trading Signals</h2>
            <p className="text-sm text-gray-400">Every signal the worker has generated, same as what&apos;s sent to Telegram</p>
          </div>
          <Button onClick={() => refetch()} size="icon" variant="ghost" className="text-white hover:bg-white/10 shrink-0">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>

        <div className="mb-6">
          <MarketStatus />
        </div>

        <div className="flex flex-wrap gap-2 sm:gap-3 mb-6">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-xs sm:text-sm text-gray-400">Timeframe:</span>
          </div>
          {timeframeOptions.map((tf) => (
            <Button
              key={tf}
              size="sm"
              variant={timeframeFilter === tf ? "default" : "outline"}
              className={
                timeframeFilter === tf ? "bg-amber-500 hover:bg-amber-600" : "border-white/20 text-white hover:bg-white/10"
              }
              onClick={() => setTimeframeFilter(tf)}
            >
              {tf === "all" ? "All" : tf.toUpperCase()}
            </Button>
          ))}

          <div className="w-px h-8 bg-white/10 hidden sm:block" />

          {STATUS_FILTERS.map((status) => (
            <Button
              key={status.value}
              size="sm"
              variant={statusFilter === status.value ? "default" : "outline"}
              className={
                statusFilter === status.value ? "bg-amber-500 hover:bg-amber-600" : "border-white/20 text-white hover:bg-white/10"
              }
              onClick={() => setStatusFilter(status.value)}
            >
              {status.label}
            </Button>
          ))}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <Card key={i} className="bg-white/5 border-white/10 backdrop-blur-xl animate-pulse">
                <div className="h-32" />
              </Card>
            ))}
          </div>
        ) : signals.length === 0 ? (
          <Card className="bg-white/5 border-white/10 backdrop-blur-xl text-center py-10 sm:py-12">
            <TrendingUp className="w-10 h-10 sm:w-12 sm:h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-sm sm:text-base">No signals found matching your filters</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {signals.map((signal) => {
              const isLong = signal.direction === "LONG";

              return (
                <Card
                  key={signal.id}
                  onClick={() => setSelectedSignalId(signal.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") setSelectedSignalId(signal.id);
                  }}
                  className="bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-4 gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0 ${
                          isLong ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {isLong ? <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6" /> : <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6" />}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <Badge variant={isLong ? "default" : "destructive"} className="font-semibold">
                            {signal.direction}
                          </Badge>
                          <Badge variant="outline" className="border-white/20 text-white">
                            {signal.timeframe.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-400 truncate">{signal.strategy_name}</p>
                      </div>
                    </div>

                    <Badge
                      variant="outline"
                      className={
                        signal.status === "active"
                          ? "bg-green-500/20 text-green-400 border-green-500/40"
                          : signal.status === "closed_tp"
                            ? "bg-green-500/20 text-green-400 border-green-500/40"
                            : signal.status === "closed_sl"
                              ? "bg-red-500/20 text-red-400 border-red-500/40"
                              : "border-white/20 text-white shrink-0"
                      }
                    >
                      {signal.status}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4 p-3 sm:p-4 rounded-lg bg-black/20">
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <Target className="w-3 h-3 text-blue-400 shrink-0" />
                        <span className="text-[10px] sm:text-xs text-gray-400">Entry</span>
                      </div>
                      <p className="text-sm sm:text-lg font-bold text-white">${signal.entry_price.toFixed(2)}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <Shield className="w-3 h-3 text-red-400 shrink-0" />
                        <span className="text-[10px] sm:text-xs text-gray-400">Stop Loss</span>
                      </div>
                      <p className="text-sm sm:text-lg font-bold text-red-400">${signal.stop_loss.toFixed(2)}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <ArrowUpRight className="w-3 h-3 text-green-400 shrink-0" />
                        <span className="text-[10px] sm:text-xs text-gray-400">Take Profit</span>
                      </div>
                      <p className="text-sm sm:text-lg font-bold text-green-400">${signal.take_profit.toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-white/10 flex-wrap gap-2">
                    <div className="flex items-center gap-4 text-xs sm:text-sm">
                      <div>
                        <span className="text-gray-400">R:R </span>
                        <span className="font-semibold text-amber-400">
                          {signal.risk_reward_ratio != null ? `1:${signal.risk_reward_ratio.toFixed(2)}` : "—"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Confidence </span>
                        <span className="font-semibold text-white">{(signal.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(signal.timestamp), { addSuffix: true })}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {!isLoading && signals.length > 0 && (
          <div className="mt-6 text-center text-sm text-gray-400">
            Showing {signals.length} of {data?.total || 0} signals
          </div>
        )}
      </section>

      {/* How it works */}
      <section className="relative py-12 sm:py-16 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3 sm:mb-4">How It Works</h2>
            <p className="text-base sm:text-lg text-gray-400">From a validated setup to a tracked outcome</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 md:gap-8">
            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <Radio className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">1. A rule fires</h3>
              <p className="text-sm sm:text-base text-gray-400">
                The worker checks XAUUSD every hour. When a validated strategy triggers, a signal is generated
                with entry, stop loss, and take profit already set.
              </p>
            </Card>

            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <BellRing className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">2. You&apos;re notified</h3>
              <p className="text-sm sm:text-base text-gray-400">
                The signal posts to Telegram and shows up here at the same time, each with a reference ID so it&apos;s
                easy to track down later.
              </p>
            </Card>

            <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">3. The outcome is tracked</h3>
              <p className="text-sm sm:text-base text-gray-400">
                Every candle is checked against the open signal. Hitting take profit, stop loss, or expiring all
                get a follow-up message and feed directly into the performance numbers above.
              </p>
            </Card>
          </div>
        </div>
      </section>

      <footer className="relative border-t border-white/10 py-6 sm:py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <div className="text-gray-400 text-xs sm:text-sm">© {new Date().getFullYear()} Gold Trader&apos;s Edge</div>
            <div className="flex gap-4 sm:gap-6">
              <Link href="/performance" className="text-gray-400 hover:text-white text-xs sm:text-sm transition-colors">
                Performance
              </Link>
              <Link href="/controls" className="text-gray-400 hover:text-white text-xs sm:text-sm transition-colors">
                Controls
              </Link>
            </div>
          </div>
        </div>
      </footer>

      <SignalDetailDialog
        signalId={selectedSignalId}
        onOpenChange={(open) => {
          if (!open) setSelectedSignalId(null);
        }}
      />
    </div>
  );
}
