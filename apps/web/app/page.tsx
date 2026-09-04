"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Zap, Shield, BarChart3, ChevronRight, CheckCircle2, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NavBar } from "@/components/layout/NavBar";
import { apiClient } from "@/lib/api/client";
import { formatR, formatProfitFactor } from "@/lib/utils";
import type { PerformanceStats, ServiceStatus } from "@/lib/types";

export default function LandingPage() {
  const stats = useQuery<PerformanceStats>({
    queryKey: ["performance-stats"],
    queryFn: () => apiClient.getPerformanceStats(),
  });
  const service = useQuery<ServiceStatus>({
    queryKey: ["service-status"],
    queryFn: () => apiClient.getServiceStatus(),
  });

  const hasResults = (stats.data?.total_closed || 0) > 0;

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-64 h-64 sm:w-96 sm:h-96 bg-amber-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-48 w-64 h-64 sm:w-96 sm:h-96 bg-orange-500/20 rounded-full blur-3xl" />
      </div>

      <NavBar />

      {/* Hero */}
      <section className="relative pt-12 pb-16 sm:pt-20 sm:pb-24 md:pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs sm:text-sm mb-5 sm:mb-6">
              <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>Live on XAUUSD · {service.data?.active_timeframes?.join(", ").toUpperCase() || "—"}</span>
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 sm:mb-6">
              Professional
              <span className="block mt-1 sm:mt-2 bg-linear-to-r from-amber-400 via-orange-500 to-amber-400 bg-clip-text text-transparent">
                Gold Trading Signals
              </span>
            </h1>

            <p className="text-base sm:text-lg md:text-xl text-gray-400 mb-8 sm:mb-10">
              A live signal service for XAUUSD, generating real-time trade alerts and reporting exactly what it
              actually earns — no dollar account behind these signals, so results are measured in R-multiples.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
              <Link href="/signals" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto bg-linear-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white h-11 sm:h-12 px-6 sm:px-8">
                  View Live Signals
                  <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5 ml-2" />
                </Button>
              </Link>
              <Link href="/performance" className="w-full sm:w-auto">
                <Button size="lg" variant="outline" className="w-full sm:w-auto border-white/20 text-white hover:bg-white/10 h-11 sm:h-12 px-6 sm:px-8">
                  See Real Performance
                </Button>
              </Link>
            </div>
          </div>

          {/* Real stats */}
          <div className="mt-12 sm:mt-16 md:mt-20 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-4xl mx-auto">
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
        </div>
      </section>

      {/* Features */}
      <section className="relative py-12 sm:py-16 md:py-20 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-3 sm:mb-4">What You Get</h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-400">Everything a signal needs to be actionable</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 md:gap-8">
            <Card className="bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">Real-Time Signals</h3>
              <p className="text-sm sm:text-base text-gray-400 mb-4 sm:mb-6">
                Instant alerts when a validated setup triggers, with every level you need to act on it.
              </p>
              <ul className="space-y-2">
                {["Entry price", "Stop loss", "Take profit", "Risk/reward ratio"].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-xs sm:text-sm text-gray-300">
                    <CheckCircle2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-400 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <Shield className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">Live Controls</h3>
              <p className="text-sm sm:text-base text-gray-400 mb-4 sm:mb-6">
                Toggle strategies and risk limits from the dashboard — changes apply to the running service.
              </p>
              <ul className="space-y-2">
                {["Per-strategy on/off", "Max risk per trade", "Max concurrent positions", "Auto-trading controls"].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-xs sm:text-sm text-gray-300">
                    <CheckCircle2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-400 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-4 sm:mb-6">
                <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-amber-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">Honest Performance</h3>
              <p className="text-sm sm:text-base text-gray-400 mb-4 sm:mb-6">
                Win rate and profit factor computed from actual TP/SL outcomes — never a hardcoded number.
              </p>
              <ul className="space-y-2">
                {["Win rate", "Profit factor", "Per-strategy breakdown", "Full trade history"].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-xs sm:text-sm text-gray-300">
                    <CheckCircle2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-400 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-12 sm:py-16 md:py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Card className="p-6 sm:p-12 bg-linear-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20 backdrop-blur-xl">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 sm:mb-6">See It Live</h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-300 mb-6 sm:mb-8">
              Every signal, every outcome, every setting — nothing hidden behind a marketing number.
            </p>
            <Link href="/signals">
              <Button size="lg" className="w-full sm:w-auto bg-linear-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 h-12 sm:h-14 px-8 sm:px-10 text-base sm:text-lg">
                View Live Signals
                <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 ml-2" />
              </Button>
            </Link>
          </Card>
        </div>
      </section>

      <footer className="relative border-t border-white/10 py-6 sm:py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <div className="text-gray-400 text-xs sm:text-sm">© {new Date().getFullYear()} Gold Trader&apos;s Edge</div>
            <div className="flex gap-4 sm:gap-6">
              <Link href="/signals" className="text-gray-400 hover:text-white text-xs sm:text-sm transition-colors">
                Signals
              </Link>
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
    </div>
  );
}
