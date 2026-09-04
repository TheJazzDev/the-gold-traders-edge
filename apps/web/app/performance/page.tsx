"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { NavBar } from "@/components/layout/NavBar";
import { PerformanceStats } from "@/components/dashboard/performance-stats";
import { RulePerformanceChart } from "@/components/dashboard/rule-performance-chart";
import { TradeHistoryTable } from "@/components/dashboard/trade-history-table";
import type { PerformanceStats as PerformanceStatsType, RulePerformance, Trade } from "@/lib/types";

export default function PerformancePage() {
  const stats = useQuery<PerformanceStatsType>({
    queryKey: ["performance-stats"],
    queryFn: () => apiClient.getPerformanceStats(),
  });
  const byRule = useQuery<RulePerformance[]>({
    queryKey: ["by-rule"],
    queryFn: () => apiClient.getByRule(),
  });
  const trades = useQuery<{ total: number; trades: Trade[] }>({
    queryKey: ["trades"],
    queryFn: () => apiClient.getTrades(1, 50),
  });

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <NavBar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6 sm:space-y-8">
        <div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-1 sm:mb-2">Performance</h1>
          <p className="text-sm text-gray-400">
            Real outcomes from the live signal service — all-time, measured in R-multiples since there&apos;s no
            dollar account behind these signals yet.
          </p>
        </div>

        <PerformanceStats data={stats.data as PerformanceStatsType} loading={stats.isLoading || !stats.data} />

        <RulePerformanceChart data={byRule.data || []} loading={byRule.isLoading} />

        <TradeHistoryTable data={trades.data?.trades || []} loading={trades.isLoading} />
      </div>
    </div>
  );
}
