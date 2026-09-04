"use client";

import { useState } from "react";
import { useSignals } from "@/lib/hooks/useSignals";
import { useServiceStatus } from "@/lib/hooks/useSettings";
import { NavBar } from "@/components/layout/NavBar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MarketStatus } from "@/components/market/MarketStatus";
import { TrendingUp, TrendingDown, Filter, RefreshCw, Clock, Target, Shield, ArrowUpRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { SignalStatus } from "@/lib/types";

const STATUS_FILTERS: { value: SignalStatus | "all"; label: string }[] = [
  { value: "all", label: "All Status" },
  { value: "pending", label: "Pending" },
  { value: "active", label: "Active" },
  { value: "closed_tp", label: "Closed (TP)" },
  { value: "closed_sl", label: "Closed (SL)" },
];

export default function SignalsPage() {
  const [timeframeFilter, setTimeframeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: serviceStatus } = useServiceStatus();
  const { data, isLoading, refetch } = useSignals({
    limit: 50,
    timeframe: timeframeFilter === "all" ? undefined : timeframeFilter,
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  const signals = data?.signals || [];
  // Timeframe options come from what the service actually runs, not an
  // aspirational list — see /v1/settings/service/status.
  const timeframeOptions = ["all", ...(serviceStatus?.active_timeframes || [])];

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 -left-48 w-64 h-64 sm:w-96 sm:h-96 bg-amber-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 -right-48 w-64 h-64 sm:w-96 sm:h-96 bg-orange-500/10 rounded-full blur-3xl" />
      </div>

      <NavBar />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="mb-6 sm:mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-1 sm:mb-2">
              Live Trading Signals
            </h1>
            <p className="text-sm text-gray-400">Real-time XAUUSD signals from the live worker</p>
          </div>
          <Button onClick={() => refetch()} size="icon" variant="ghost" className="text-white hover:bg-white/10 shrink-0">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>

        <div className="mb-6 sm:mb-8">
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
                <Card key={signal.id} className="bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
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
                        <span className="font-semibold text-amber-400">1:{signal.risk_reward_ratio.toFixed(2)}</span>
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
      </div>
    </div>
  );
}
