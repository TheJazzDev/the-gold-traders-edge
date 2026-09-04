"use client";

import type { Trade } from "@/lib/types";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { formatR } from "@/lib/utils";

interface TradeHistoryTableProps {
  data: Trade[];
  loading?: boolean;
}

function formatDate(dateString: string | null) {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DirectionBadge({ direction }: { direction: Trade["direction"] }) {
  const isLong = direction === "LONG";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${
        isLong
          ? "bg-green-500/20 text-green-400 border border-green-500/30"
          : "bg-red-500/20 text-red-400 border border-red-500/30"
      }`}
    >
      {isLong ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {direction}
    </span>
  );
}

function StatusBadge({ status }: { status: Trade["status"] }) {
  const tone =
    status === "closed_tp"
      ? "bg-green-500/20 text-green-400 border-green-500/30"
      : status === "closed_sl"
        ? "bg-red-500/20 text-red-400 border-red-500/30"
        : "bg-white/10 text-white/60 border-white/20";
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold border ${tone}`}>{status}</span>;
}

export function TradeHistoryTable({ data, loading }: TradeHistoryTableProps) {
  if (loading) {
    return <div className="h-64 sm:h-96 glass rounded-xl animate-pulse" />;
  }

  if (data.length === 0) {
    return <div className="glass rounded-xl p-6 sm:p-8 text-center text-sm text-white/50">No resolved trades yet</div>;
  }

  return (
    <div className="glass rounded-xl p-4 sm:p-6">
      <div className="mb-4 sm:mb-6">
        <h3 className="text-base sm:text-xl font-bold text-white">Trade History</h3>
        <p className="text-xs sm:text-sm text-white/60 mt-1">Entry, exit, and R-multiple for every resolved signal</p>
      </div>

      {/* Mobile: stacked cards */}
      <div className="space-y-3 sm:hidden">
        {data.map((trade) => (
          <div key={trade.id} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">{trade.signal_name}</span>
              <DirectionBadge direction={trade.direction} />
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-white/70">
              <span>Entry: {trade.entry_price.toFixed(2)}</span>
              <span>Exit: {trade.exit_price?.toFixed(2) ?? "-"}</span>
              <span>{formatDate(trade.entry_time)}</span>
              <span>{formatDate(trade.exit_time)}</span>
            </div>
            <div className="flex items-center justify-between mt-2">
              <StatusBadge status={trade.status} />
              <span className={`font-bold text-sm ${trade.r_multiple >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatR(trade.r_multiple)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop: table */}
      <div className="hidden sm:block overflow-x-auto rounded-xl">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              <th className="text-left py-3 px-3 font-semibold text-white/70">Signal</th>
              <th className="text-left py-3 px-3 font-semibold text-white/70">Direction</th>
              <th className="text-left py-3 px-3 font-semibold text-white/70">Entry</th>
              <th className="text-left py-3 px-3 font-semibold text-white/70">Exit</th>
              <th className="text-left py-3 px-3 font-semibold text-white/70">Status</th>
              <th className="text-right py-3 px-3 font-semibold text-white/70">R:R</th>
              <th className="text-right py-3 px-3 font-semibold text-white/70">Result</th>
            </tr>
          </thead>
          <tbody>
            {data.map((trade) => (
              <tr key={trade.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                <td className="py-3 px-3 text-white font-medium">{trade.signal_name}</td>
                <td className="py-3 px-3">
                  <DirectionBadge direction={trade.direction} />
                </td>
                <td className="py-3 px-3 text-white/60 text-xs">
                  {trade.entry_price.toFixed(2)}
                  <br />
                  {formatDate(trade.entry_time)}
                </td>
                <td className="py-3 px-3 text-white/60 text-xs">
                  {trade.exit_price?.toFixed(2) ?? "-"}
                  <br />
                  {formatDate(trade.exit_time)}
                </td>
                <td className="py-3 px-3">
                  <StatusBadge status={trade.status} />
                </td>
                <td className="py-3 px-3 text-right text-white/80">
                  {trade.risk_reward ? `1:${trade.risk_reward.toFixed(2)}` : "-"}
                </td>
                <td className="py-3 px-3 text-right">
                  <span className={`font-bold ${trade.r_multiple >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {formatR(trade.r_multiple)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
