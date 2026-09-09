"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useSettingsByCategory,
  useServiceStatus,
  useStrategies,
  useUpdateSetting,
} from "@/lib/hooks/useSettings";
import { useSignals } from "@/lib/hooks/useSignals";
import { NavBar } from "@/components/layout/NavBar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { formatProfitFactor } from "@/lib/utils";
import { Server, Zap, Shield, CheckCircle2, XCircle, Play, Square } from "lucide-react";
import type { Setting, StrategyPerformance } from "@/lib/types";

function findSetting(settings: Setting[] | undefined, key: string) {
  return settings?.find((s) => s.key === key);
}

export default function ControlsPage() {
  const { data: settingsByCategory } = useSettingsByCategory();
  const { data: serviceStatus } = useServiceStatus();
  const { data: strategies } = useStrategies();
  const { data: recent } = useSignals({ limit: 5 });
  const updateSetting = useUpdateSetting();

  const tradingSettings = settingsByCategory?.trading;
  const riskSettings = settingsByCategory?.risk_management;

  const autoTradingSetting = findSetting(tradingSettings, "auto_trading_enabled");
  const dryRunSetting = findSetting(tradingSettings, "dry_run_mode");
  const maxRiskSetting = findSetting(riskSettings, "max_risk_per_trade");
  const maxPositionsSetting = findSetting(riskSettings, "max_positions");

  // Local edits override the server value until saved; falls back to the
  // real setting once it loads rather than seeding state via an effect.
  const [maxRiskOverride, setMaxRiskOverride] = useState<number | null>(null);
  const [maxPositionsOverride, setMaxPositionsOverride] = useState<number | null>(null);

  const maxRisk = maxRiskOverride ?? (maxRiskSetting ? Number(maxRiskSetting.typed_value) : null);
  const maxPositions = maxPositionsOverride ?? (maxPositionsSetting ? Number(maxPositionsSetting.typed_value) : null);

  const autoTrading = autoTradingSetting?.typed_value === true;
  const dryRun = dryRunSetting?.typed_value === true;
  // Scoped to XAUUSD only: enabled_strategies is gold's setting alone, and
  // once enabled_forex_symbols lets a GBPUSD/EURUSD row's `enabled` go
  // true, including those rows here would smuggle their shared rule key
  // ("asian_range_london_breakout") into `next` below the next time someone
  // legitimately toggles a XAUUSD row.
  const enabledStrategies = strategies?.filter((s) => s.symbol === "XAUUSD" && s.enabled).map((s) => s.key) || [];
  const xauStrategiesCount = strategies?.filter((s) => s.symbol === "XAUUSD").length || 0;

  // Only XAUUSD's rows are backed by the enabled_strategies setting.
  // GBPUSD/EURUSD share ForexSessionStrategy's single rule name
  // (asian_range_london_breakout) with each other, so writing their
  // toggle into enabled_strategies would corrupt gold's own rule list —
  // their toggle is gated off below instead (see the Switch's `disabled`
  // prop). Enabling either forex symbol live is a separate, deliberate
  // decision (enabled_forex_symbols), not made from this page yet.
  const toggleStrategy = (strategy: StrategyPerformance) => {
    // Belt-and-braces: the real corruption paths are already closed above
    // (the Switch is `disabled` for non-XAUUSD rows, and enabledStrategies
    // is scoped to XAUUSD-only), but guarding here too means this function
    // itself can never write a forex rule name into enabled_strategies,
    // even if a future edit removed one of those guards.
    if (strategy.symbol !== "XAUUSD") return;
    const key = strategy.key;
    const next = enabledStrategies.includes(key)
      ? enabledStrategies.filter((k) => k !== key)
      : [...enabledStrategies, key];
    updateSetting.mutate({ key: "enabled_strategies", value: next });
  };

  const saveRiskSettings = () => {
    if (maxRisk !== null) updateSetting.mutate({ key: "max_risk_per_trade", value: maxRisk });
    if (maxPositions !== null) updateSetting.mutate({ key: "max_positions", value: maxPositions });
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-64 h-64 sm:w-96 sm:h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-64 h-64 sm:w-96 sm:h-96 bg-blue-500/10 rounded-full blur-3xl" />
      </div>

      <NavBar />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-1 sm:mb-2">Controls</h1>
          <p className="text-sm text-gray-400">Live settings for the signal service — every toggle here actually changes what the worker does</p>
        </div>

        <Card className="bg-linear-to-br from-purple-500/10 to-blue-500/10 border-purple-500/20 backdrop-blur-xl mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-purple-500/20 flex items-center justify-center shrink-0">
                <Server className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-semibold text-white mb-0.5 sm:mb-1">Service Status</h3>
                <p className="text-xs sm:text-sm text-gray-400">
                  Data feed: {serviceStatus?.data_feed_type || "—"} • Timeframe:{" "}
                  {serviceStatus?.active_timeframes?.join(", ") || "—"}
                </p>
              </div>
            </div>
            {serviceStatus?.status === "running" ? (
              <Badge className="bg-green-500/20 text-green-400 border-green-500/40 w-fit">
                <Play className="w-3 h-3 mr-1" />
                Running
              </Badge>
            ) : (
              <Badge variant="secondary" className="w-fit">
                <Square className="w-3 h-3 mr-1" />
                Stopped
              </Badge>
            )}
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Trading Controls */}
          <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-4 sm:mb-6">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
              </div>
              <h2 className="text-base sm:text-xl font-bold text-white">Trading Controls</h2>
            </div>

            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between p-3 sm:p-4 rounded-lg bg-black/20">
                <div className="pr-3">
                  <Label className="text-sm sm:text-base font-medium text-white">Auto-Trading</Label>
                  <p className="text-xs sm:text-sm text-gray-400 mt-1">Execute signals automatically on MT5</p>
                </div>
                <Switch
                  checked={autoTrading}
                  onCheckedChange={(checked) => updateSetting.mutate({ key: "auto_trading_enabled", value: checked })}
                />
              </div>

              <div className="flex items-center justify-between p-3 sm:p-4 rounded-lg bg-black/20">
                <div className="pr-3">
                  <Label className="text-sm sm:text-base font-medium text-white">Dry Run Mode</Label>
                  <p className="text-xs sm:text-sm text-gray-400 mt-1">Simulate trades without execution</p>
                </div>
                <Switch
                  checked={dryRun}
                  onCheckedChange={(checked) => updateSetting.mutate({ key: "dry_run_mode", value: checked })}
                />
              </div>

              {autoTrading && !dryRun && (
                <div className="p-3 sm:p-4 rounded-lg border border-red-500/20 bg-red-500/5">
                  <div className="flex items-start gap-2">
                    <XCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs sm:text-sm font-medium text-red-400 mb-1">Live Trading Enabled</p>
                      <p className="text-xs text-gray-400">Real trades will be executed. Ensure MT5 is configured correctly.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Risk Settings */}
          <Card className="bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-4 sm:mb-6">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
              </div>
              <h2 className="text-base sm:text-xl font-bold text-white">Risk Settings</h2>
            </div>

            <div className="space-y-5 sm:space-y-6">
              {maxRiskSetting && maxRisk !== null && (
                <div>
                  <div className="flex items-center justify-between mb-2 sm:mb-3">
                    <Label className="text-xs sm:text-sm text-gray-300">Max Risk Per Trade</Label>
                    <span className="text-base sm:text-lg font-bold text-white">{maxRisk.toFixed(1)}%</span>
                  </div>
                  <Slider
                    value={[maxRisk]}
                    min={maxRiskSetting.min_value ?? 0}
                    max={maxRiskSetting.max_value ?? 10}
                    step={0.1}
                    onValueChange={([value]) => setMaxRiskOverride(value)}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Range: {maxRiskSetting.min_value}% – {maxRiskSetting.max_value}%
                  </p>
                </div>
              )}

              {maxPositionsSetting && maxPositions !== null && (
                <div>
                  <div className="flex items-center justify-between mb-2 sm:mb-3">
                    <Label className="text-xs sm:text-sm text-gray-300">Max Concurrent Positions</Label>
                    <span className="text-base sm:text-lg font-bold text-white">{maxPositions}</span>
                  </div>
                  <Slider
                    value={[maxPositions]}
                    min={maxPositionsSetting.min_value ?? 1}
                    max={maxPositionsSetting.max_value ?? 20}
                    step={1}
                    onValueChange={([value]) => setMaxPositionsOverride(value)}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Range: {maxPositionsSetting.min_value} – {maxPositionsSetting.max_value}
                  </p>
                </div>
              )}

              <Button onClick={saveRiskSettings} className="w-full bg-linear-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700">
                Save Risk Settings
              </Button>
            </div>
          </Card>

          {/* Strategy Management */}
          <Card className="bg-white/5 border-white/10 backdrop-blur-xl lg:col-span-2">
            <div className="flex items-center justify-between mb-4 sm:mb-6 flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 sm:w-5 sm:h-5 text-green-400" />
                </div>
                <div>
                  <h2 className="text-base sm:text-xl font-bold text-white">Strategy Management</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {enabledStrategies.length} / {xauStrategiesCount} XAUUSD active — applies on the next candle close, no restart needed
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2 sm:space-y-3">
              {strategies?.map((strategy) => (
                <div
                  key={`${strategy.symbol}-${strategy.key}`}
                  className="flex items-center justify-between gap-3 p-3 sm:p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all"
                >
                  <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                    <Switch
                      checked={strategy.enabled}
                      disabled={strategy.symbol !== "XAUUSD"}
                      onCheckedChange={() => toggleStrategy(strategy)}
                    />
                    <div className="min-w-0">
                      <p className="text-sm sm:text-base font-medium text-white mb-0.5 sm:mb-1 truncate">
                        {strategy.name} <span className="text-gray-500 font-normal">· {strategy.symbol}</span>
                      </p>
                      {strategy.validated ? (
                        <div className="flex items-center gap-2 sm:gap-3 text-xs text-gray-400 flex-wrap">
                          <span>
                            Win rate: <span className="text-white font-medium">{strategy.win_rate?.toFixed(1)}%</span>
                          </span>
                          <span>
                            PF:{" "}
                            <span className={strategy.profit_factor && strategy.profit_factor >= 1 ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
                              {formatProfitFactor(strategy.profit_factor)}
                            </span>
                          </span>
                          <span>{strategy.total_trades} trades</span>
                        </div>
                      ) : (
                        <span className="text-xs text-amber-400">Not yet validated</span>
                      )}
                    </div>
                  </div>
                  {strategy.validated && strategy.profit_factor !== null && strategy.profit_factor < 1 && (
                    <Badge variant="outline" className="border-red-500/40 text-red-400 shrink-0 hidden sm:inline-flex">
                      Unprofitable
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* Recent Signals preview */}
          <Card className="bg-white/5 border-white/10 backdrop-blur-xl lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base sm:text-xl font-bold text-white">Recent Signals</h2>
              <Link href="/#signals">
                <Button variant="outline" size="sm" className="border-white/20 text-white hover:bg-white/10">
                  View All
                </Button>
              </Link>
            </div>
            {(recent?.signals.length || 0) === 0 ? (
              <p className="text-sm text-gray-400 text-center py-6">No signals yet</p>
            ) : (
              <div className="space-y-2">
                {recent!.signals.map((signal) => (
                  <div key={signal.id} className="flex items-center justify-between p-3 rounded-lg bg-black/20">
                    <div className="flex items-center gap-3 min-w-0">
                      <Badge variant={signal.direction === "LONG" ? "default" : "destructive"}>{signal.direction}</Badge>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-white truncate">
                          {signal.symbol} • {signal.timeframe.toUpperCase()}
                        </p>
                        <p className="text-xs text-gray-400 truncate">{signal.strategy_name}</p>
                      </div>
                    </div>
                    <p className="text-sm font-bold text-white shrink-0">${signal.entry_price.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
