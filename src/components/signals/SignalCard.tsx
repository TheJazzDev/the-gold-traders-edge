"use client";

import {
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  Clock,
  Zap,
  ChevronRight,
} from "lucide-react";
import type { Signal } from "@/types";
import { formatPrice, timeAgo, cn } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  onSelect?: (signal: Signal) => void;
  compact?: boolean;
}

export function SignalCard({ signal, onSelect, compact = false }: SignalCardProps) {
  const isBuy = signal.direction === "BUY";
  const DirectionIcon = isBuy ? TrendingUp : TrendingDown;

  const statusLabels: Record<string, string> = {
    PENDING: "Pending",
    ACTIVE: "Active",
    TP1_HIT: "TP1 Hit",
    TP2_HIT: "TP2 Hit",
    SL_HIT: "SL Hit",
    CANCELLED: "Cancelled",
    EXPIRED: "Expired",
  };

  const statusClasses: Record<string, string> = {
    PENDING: "status-pending",
    ACTIVE: "status-active",
    TP1_HIT: "status-hit-tp",
    TP2_HIT: "status-hit-tp",
    SL_HIT: "status-hit-sl",
    CANCELLED: "bg-secondary-700/50 text-secondary-400 border-secondary-600/30",
    EXPIRED: "bg-secondary-700/50 text-secondary-400 border-secondary-600/30",
  };

  if (compact) {
    return (
      <button
        onClick={() => onSelect?.(signal)}
        className="w-full signal-card flex items-center justify-between gap-4 hover:scale-[1.01]"
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center",
              isBuy ? "bg-profit/20" : "bg-loss/20"
            )}
          >
            <DirectionIcon
              className={cn("w-5 h-5", isBuy ? "text-profit" : "text-loss")}
            />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "font-semibold",
                  isBuy ? "text-profit" : "text-loss"
                )}
              >
                {signal.direction}
              </span>
              <span className={statusClasses[signal.status]}>
                {statusLabels[signal.status]}
              </span>
            </div>
            <p className="text-sm text-secondary-400">
              Entry: {formatPrice(signal.entryZone.low)} -{" "}
              {formatPrice(signal.entryZone.high)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-medium text-white">
              RR {signal.riskRewardRatio.toFixed(1)}:1
            </p>
            <p className="text-xs text-secondary-400">
              {timeAgo(signal.createdAt)}
            </p>
          </div>
          <ChevronRight className="w-4 h-4 text-secondary-500" />
        </div>
      </button>
    );
  }

  return (
    <div
      className={cn(
        "signal-card",
        signal.status === "ACTIVE" && "glow-gold border-primary-500/30"
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center",
              isBuy ? "bg-profit/20" : "bg-loss/20"
            )}
          >
            <DirectionIcon
              className={cn("w-6 h-6", isBuy ? "text-profit" : "text-loss")}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-xl font-bold",
                  isBuy ? "text-profit" : "text-loss"
                )}
              >
                {signal.direction} XAUUSD
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className={statusClasses[signal.status]}>
                {statusLabels[signal.status]}
              </span>
              <span className="text-xs text-secondary-400">
                {signal.timeframe.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-primary-400">
            <Zap className="w-4 h-4" />
            <span className="font-semibold">
              {Math.round(signal.confidenceScore * 100)}%
            </span>
          </div>
          <p className="text-xs text-secondary-400 mt-1">Confidence</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 rounded-xl bg-secondary-800/50">
          <div className="flex items-center gap-2 text-secondary-400 mb-1">
            <Target className="w-4 h-4" />
            <span className="text-xs uppercase tracking-wider">Entry Zone</span>
          </div>
          <p className="font-mono font-semibold text-white">
            {formatPrice(signal.entryZone.low)} - {formatPrice(signal.entryZone.high)}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-secondary-800/50">
          <div className="flex items-center gap-2 text-secondary-400 mb-1">
            <Shield className="w-4 h-4" />
            <span className="text-xs uppercase tracking-wider">Stop Loss</span>
          </div>
          <p className="font-mono font-semibold text-loss">
            {formatPrice(signal.stopLoss)}
          </p>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between p-3 rounded-xl bg-profit/10 border border-profit/20">
          <span className="text-sm text-profit">Take Profit 1</span>
          <span className="font-mono font-semibold text-profit">
            {formatPrice(signal.takeProfit1)}
          </span>
        </div>
        {signal.takeProfit2 && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-profit/5 border border-profit/10">
            <span className="text-sm text-profit/80">Take Profit 2</span>
            <span className="font-mono font-semibold text-profit/80">
              {formatPrice(signal.takeProfit2)}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-secondary-700/50">
        <div className="flex items-center gap-4">
          <div>
            <p className="text-xs text-secondary-400">Risk:Reward</p>
            <p className="font-semibold text-primary-400">
              1:{signal.riskRewardRatio.toFixed(1)}
            </p>
          </div>
          {signal.patterns.length > 0 && (
            <div>
              <p className="text-xs text-secondary-400">Pattern</p>
              <p className="text-sm text-white">{signal.patterns[0]}</p>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 text-secondary-400">
          <Clock className="w-4 h-4" />
          <span className="text-xs">{timeAgo(signal.createdAt)}</span>
        </div>
      </div>

      {signal.analysis && (
        <div className="mt-4 p-3 rounded-xl bg-secondary-800/30 border border-secondary-700/30">
          <p className="text-sm text-secondary-300">{signal.analysis}</p>
        </div>
      )}
    </div>
  );
}
