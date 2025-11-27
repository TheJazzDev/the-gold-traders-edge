"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Target,
  TrendingUp,
  Percent,
  RefreshCw,
  Bell,
  BellOff,
} from "lucide-react";
import { SignalCard } from "@/components/signals/SignalCard";
import { StatsCard } from "@/components/ui/StatsCard";
import { toast } from "@/components/ui/Toaster";
import { usePriceTicker } from "@/hooks/usePriceTicker";
import { useNotificationPermission } from "@/hooks/useNotifications";
import { useSignalStore, useTradeStats } from "@/store";
import { fetchCandleData } from "@/services/market";
import { analyzeTechnicals, generateSignal } from "@/services/analysis";
import { cn } from "@/lib/utils";
import type { Signal } from "@/types";

export default function Dashboard() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [marketAnalysis, setMarketAnalysis] = useState<{
    trend: string;
    strength: number;
    rsi: number;
  } | null>(null);

  const { currentPrice } = usePriceTicker();
  const { isSupported, isGranted, requestPermission } = useNotificationPermission();
  const { signals, addSignal } = useSignalStore();
  const stats = useTradeStats();

  const activeSignals = signals.filter(
    (s) => s.status === "PENDING" || s.status === "ACTIVE"
  );

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const candles = await fetchCandleData("1h");
      const analysis = analyzeTechnicals(candles);

      setMarketAnalysis({
        trend: analysis.trend,
        strength: analysis.strength,
        rsi: analysis.indicators.rsi,
      });

      const newSignal = generateSignal(candles, analysis);

      if (newSignal) {
        const existingPending = signals.find(
          (s) =>
            s.status === "PENDING" &&
            s.direction === newSignal.direction &&
            Math.abs(s.entryZone.low - newSignal.entryZone.low) < 5
        );

        if (!existingPending) {
          addSignal(newSignal);
          toast({
            type: "success",
            title: "New Signal Detected!",
            message: `${newSignal.direction} opportunity with ${Math.round(newSignal.confidenceScore * 100)}% confidence`,
          });
        }
      }
    } catch (error) {
      console.error("Analysis failed:", error);
      toast({
        type: "error",
        title: "Analysis Failed",
        message: "Could not complete market analysis",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    runAnalysis();
    const interval = setInterval(runAnalysis, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleNotificationToggle = async () => {
    if (!isGranted) {
      const granted = await requestPermission();
      if (granted) {
        toast({
          type: "success",
          title: "Notifications Enabled",
          message: "You'll receive alerts for new trading signals",
        });
      }
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">
            Dashboard
          </h1>
          <p className="text-secondary-400 mt-1">
            Real-time XAUUSD analysis and trading signals
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isSupported && (
            <button
              onClick={handleNotificationToggle}
              className={cn(
                "btn-secondary",
                isGranted && "bg-profit/20 border-profit/30 text-profit"
              )}
            >
              {isGranted ? (
                <>
                  <Bell className="w-4 h-4" />
                  Alerts On
                </>
              ) : (
                <>
                  <BellOff className="w-4 h-4" />
                  Enable Alerts
                </>
              )}
            </button>
          )}
          <button
            onClick={runAnalysis}
            disabled={isAnalyzing}
            className="btn-primary"
          >
            <RefreshCw
              className={cn("w-4 h-4", isAnalyzing && "animate-spin")}
            />
            {isAnalyzing ? "Analyzing..." : "Refresh Analysis"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Win Rate"
          value={`${stats.winRate.toFixed(1)}%`}
          subtitle={`${stats.totalSignals} total signals`}
          icon={<Percent className="w-5 h-5 text-primary-400" />}
          trend={stats.winRate >= 60 ? "up" : stats.winRate < 40 ? "down" : "neutral"}
        />
        <StatsCard
          title="Active Signals"
          value={stats.activeSignals}
          subtitle="Pending & Active"
          icon={<Activity className="w-5 h-5 text-blue-400" />}
        />
        <StatsCard
          title="Total Pips"
          value={stats.totalPips >= 0 ? `+${stats.totalPips.toFixed(0)}` : stats.totalPips.toFixed(0)}
          subtitle="All time"
          icon={<Target className="w-5 h-5 text-profit" />}
          trend={stats.totalPips >= 0 ? "up" : "down"}
        />
        <StatsCard
          title="Market Trend"
          value={marketAnalysis?.trend || "—"}
          subtitle={marketAnalysis ? `${marketAnalysis.strength}% strength` : "Analyzing..."}
          icon={<TrendingUp className="w-5 h-5 text-primary-400" />}
          trend={
            marketAnalysis?.trend === "BULLISH"
              ? "up"
              : marketAnalysis?.trend === "BEARISH"
              ? "down"
              : "neutral"
          }
        />
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-display font-semibold text-white">
            Active Signals
          </h2>
          <span className="text-sm text-secondary-400">
            {activeSignals.length} active
          </span>
        </div>

        {activeSignals.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-secondary-800/50 flex items-center justify-center">
              <Target className="w-10 h-10 text-secondary-500" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              No Active Signals
            </h3>
            <p className="text-sm text-secondary-400 max-w-md mx-auto">
              The system is analyzing the market. New signals will appear here
              when high-probability setups are detected.
            </p>
            {marketAnalysis && (
              <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary-800/30 border border-secondary-700/30">
                <span className="text-sm text-secondary-400">Current Market:</span>
                <span
                  className={cn(
                    "font-semibold",
                    marketAnalysis.trend === "BULLISH" && "text-profit",
                    marketAnalysis.trend === "BEARISH" && "text-loss",
                    marketAnalysis.trend === "NEUTRAL" && "text-secondary-300"
                  )}
                >
                  {marketAnalysis.trend}
                </span>
                <span className="text-secondary-500">•</span>
                <span className="text-sm text-secondary-300">
                  {marketAnalysis.strength}% strength
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="grid lg:grid-cols-2 gap-4">
            {activeSignals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        )}

        {marketAnalysis && activeSignals.length > 0 && (
          <div className="glass-card p-6">
            <h3 className="font-semibold text-white mb-4">Market Overview</h3>
            <div className="grid grid-cols-3 gap-6">
              <div className="space-y-2">
                <span className="text-sm text-secondary-400">Trend</span>
                <div
                  className={cn(
                    "text-xl font-bold",
                    marketAnalysis.trend === "BULLISH" && "text-profit",
                    marketAnalysis.trend === "BEARISH" && "text-loss",
                    marketAnalysis.trend === "NEUTRAL" && "text-secondary-300"
                  )}
                >
                  {marketAnalysis.trend}
                </div>
              </div>
              <div className="space-y-2">
                <span className="text-sm text-secondary-400">Strength</span>
                <div className="space-y-2">
                  <div className="text-xl font-bold text-white">
                    {marketAnalysis.strength}%
                  </div>
                  <div className="w-full h-2 bg-secondary-800 rounded-full overflow-hidden">
                    <div
                      className="h-full gold-gradient rounded-full transition-all duration-500"
                      style={{ width: `${marketAnalysis.strength}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <span className="text-sm text-secondary-400">RSI</span>
                <div
                  className={cn(
                    "text-xl font-bold font-mono",
                    marketAnalysis.rsi > 70 && "text-loss",
                    marketAnalysis.rsi < 30 && "text-profit",
                    marketAnalysis.rsi >= 30 &&
                      marketAnalysis.rsi <= 70 &&
                      "text-white"
                  )}
                >
                  {marketAnalysis.rsi.toFixed(1)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
