'use client';

import { formatCurrency, formatPercent } from "@/lib/utils";
import type { TradeDetail } from "@/lib/api";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface TradeHistoryTableProps {
  data: TradeDetail[];
  loading?: boolean;
}

export function TradeHistoryTable({ data, loading }: TradeHistoryTableProps) {
  if (loading) {
    return (
      <div className="h-96 bg-white/5 rounded-xl animate-pulse"></div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-white/50">No trades found</p>
      </div>
    );
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-2xl">📋</span>
          Trade History
        </h3>
        <p className="text-sm text-white/60 mt-1">Detailed view of all trades with entry, stop-loss, and take-profit levels</p>
      </div>

      <div className="overflow-x-auto rounded-xl">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              <th className="text-left py-4 px-3 font-semibold text-white/70">ID</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Signal</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Direction</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Entry</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Entry Price</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">SL</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">TP</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Exit</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Exit Price</th>
              <th className="text-left py-4 px-3 font-semibold text-white/70">Status</th>
              <th className="text-right py-4 px-3 font-semibold text-white/70">P&L</th>
              <th className="text-right py-4 px-3 font-semibold text-white/70">R:R</th>
            </tr>
          </thead>
          <tbody>
            {data.map((trade, index) => (
              <tr
                key={trade.id}
                className={`border-b border-white/5 hover:bg-white/5 transition-colors ${
                  index % 2 === 0 ? 'bg-white/[0.02]' : ''
                }`}
              >
                <td className="py-3 px-3 text-white/80 font-mono text-xs">#{trade.id}</td>
                <td className="py-3 px-3 text-white font-medium">{trade.signal_name}</td>
                <td className="py-3 px-3">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                    trade.direction === 'long'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}>
                    {trade.direction === 'long' ? (
                      <ArrowUpRight className="h-3 w-3" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3" />
                    )}
                    {trade.direction.toUpperCase()}
                  </span>
                </td>
                <td className="py-3 px-3 text-white/60 text-xs">
                  {formatDate(trade.entry_time)}
                </td>
                <td className="py-3 px-3 text-white font-mono">
                  {formatCurrency(trade.entry_price)}
                </td>
                <td className="py-3 px-3 text-red-400 font-mono">
                  {formatCurrency(trade.stop_loss)}
                </td>
                <td className="py-3 px-3 text-green-400 font-mono">
                  {trade.take_profit ? formatCurrency(trade.take_profit) : '-'}
                </td>
                <td className="py-3 px-3 text-white/60 text-xs">
                  {formatDate(trade.exit_time)}
                </td>
                <td className="py-3 px-3 text-white font-mono">
                  {trade.exit_price ? formatCurrency(trade.exit_price) : '-'}
                </td>
                <td className="py-3 px-3">
                  <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold ${
                    trade.status === 'Closed Tp'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : trade.status === 'Closed Sl'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-white/10 text-white/60 border border-white/20'
                  }`}>
                    {trade.status}
                  </span>
                </td>
                <td className="py-3 px-3 text-right">
                  <div className="flex flex-col items-end">
                    <span className={`font-bold ${
                      trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                    </span>
                    <span className={`text-xs ${
                      trade.pnl >= 0 ? 'text-green-400/70' : 'text-red-400/70'
                    }`}>
                      ({trade.pnl >= 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%)
                    </span>
                  </div>
                </td>
                <td className="py-3 px-3 text-right text-white/80 font-medium">
                  {trade.risk_reward ? `1:${trade.risk_reward.toFixed(2)}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-white/40">
        <p><span className="text-red-400">SL:</span> Stop Loss | <span className="text-green-400">TP:</span> Take Profit | <span className="text-amber-400">R:R:</span> Risk:Reward Ratio</p>
        <p>Showing {data.length} trades total</p>
      </div>
    </div>
  );
}
