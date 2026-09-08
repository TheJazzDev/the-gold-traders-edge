"use client";

import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, format } from "date-fns";
import { Target, Shield, ArrowUpRight, Clock, Hash } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api/client";
import { formatR, parseApiDate } from "@/lib/utils";
import type { SignalDetail } from "@/lib/types";

interface SignalDetailDialogProps {
  signalId: number | null;
  onOpenChange: (open: boolean) => void;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Open — tracking",
  active: "Active",
  closed_tp: "Closed — Take Profit hit",
  closed_sl: "Closed — Stop Loss hit",
  closed_manual: "Closed manually",
  cancelled: "Cancelled",
};

export function SignalDetailDialog({ signalId, onOpenChange }: SignalDetailDialogProps) {
  const { data: signal, isLoading } = useQuery<SignalDetail>({
    queryKey: ["signal", signalId],
    queryFn: () => apiClient.getSignal(signalId as number),
    enabled: signalId !== null,
  });

  const isClosed = signal?.status.startsWith("closed") ?? false;
  const realizedR =
    signal?.pnl_pips != null && signal?.risk_pips ? signal.pnl_pips / signal.risk_pips : null;

  return (
    <Dialog open={signalId !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        {isLoading || !signal ? (
          <div className="space-y-3 py-2">
            <div className="h-6 w-2/3 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-1/2 bg-white/10 rounded animate-pulse" />
            <div className="h-24 bg-white/10 rounded animate-pulse mt-4" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2 flex-wrap">
                <DialogTitle>{signal.strategy_name}</DialogTitle>
                <Badge variant={signal.direction === "LONG" ? "default" : "destructive"}>
                  {signal.direction}
                </Badge>
              </div>
              <DialogDescription className="flex items-center gap-1.5">
                {signal.reference_id ? (
                  <>
                    <Hash className="h-3 w-3" /> {signal.reference_id}
                  </>
                ) : (
                  `Signal #${signal.id} (generated before reference IDs existed)`
                )}
                {" · "}
                {signal.symbol} {signal.timeframe.toUpperCase()}
              </DialogDescription>
            </DialogHeader>

            <div>
              <Badge
                variant="outline"
                className={
                  signal.status === "closed_tp"
                    ? "bg-green-500/20 text-green-400 border-green-500/40"
                    : signal.status === "closed_sl"
                      ? "bg-red-500/20 text-red-400 border-red-500/40"
                      : signal.status === "active"
                        ? "bg-blue-500/20 text-blue-400 border-blue-500/40"
                        : "border-white/20 text-white"
                }
              >
                {STATUS_LABEL[signal.status] ?? signal.status}
              </Badge>
            </div>

            <div className="grid grid-cols-3 gap-2 sm:gap-4 p-3 sm:p-4 rounded-lg bg-black/20">
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

            <div className="flex items-center gap-4 text-xs sm:text-sm flex-wrap">
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
              <div className="flex items-center gap-1 text-gray-500">
                <Clock className="w-3 h-3" />
                Generated {formatDistanceToNow(parseApiDate(signal.created_at), { addSuffix: true })}
              </div>
            </div>

            {isClosed && (
              <div className="rounded-lg border border-white/10 p-3 sm:p-4 space-y-2">
                <h4 className="text-xs sm:text-sm font-semibold text-white/70">Outcome</h4>
                <div className="grid grid-cols-2 gap-2 sm:gap-4 text-xs sm:text-sm">
                  <div>
                    <span className="text-gray-400 block">Exit price</span>
                    <span className="font-semibold text-white">
                      {signal.actual_exit != null ? `$${signal.actual_exit.toFixed(2)}` : "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400 block">Realized</span>
                    <span className={`font-semibold ${realizedR != null && realizedR >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {realizedR != null ? formatR(realizedR) : "—"}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-400 block">Closed</span>
                    <span className="font-semibold text-white">
                      {signal.closed_at ? format(parseApiDate(signal.closed_at), "MMM d, yyyy 'at' HH:mm") : "—"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {signal.notes && (
              <div>
                <h4 className="text-xs sm:text-sm font-semibold text-white/70 mb-1">Why this fired</h4>
                <p className="text-xs sm:text-sm text-white/60">{signal.notes}</p>
              </div>
            )}

            {signal.error_message && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs sm:text-sm text-red-300">
                {signal.error_message}
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
