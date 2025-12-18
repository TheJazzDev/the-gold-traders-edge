'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Detailed view of all trades with entry, stop-loss, and take-profit levels</CardDescription>
        </CardHeader>
        <CardContent className="h-96 animate-pulse bg-gray-100 rounded"></CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Detailed view of all trades with entry, stop-loss, and take-profit levels</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-gray-500 py-8">No trades found</p>
        </CardContent>
      </Card>
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
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Trade History</CardTitle>
        <CardDescription>Detailed view of all trades with entry, stop-loss, and take-profit levels</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-2 font-semibold text-gray-700">ID</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Signal</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Direction</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Entry</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Entry Price</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">SL</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">TP</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Exit</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Exit Price</th>
                <th className="text-left py-3 px-2 font-semibold text-gray-700">Status</th>
                <th className="text-right py-3 px-2 font-semibold text-gray-700">P&L</th>
                <th className="text-right py-3 px-2 font-semibold text-gray-700">R:R</th>
              </tr>
            </thead>
            <tbody>
              {data.map((trade) => (
                <tr
                  key={trade.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-3 px-2 text-gray-900">#{trade.id}</td>
                  <td className="py-3 px-2 text-gray-900 font-medium">{trade.signal_name}</td>
                  <td className="py-3 px-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                      trade.direction === 'long'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {trade.direction === 'long' ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {trade.direction.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-gray-700 text-xs">
                    {formatDate(trade.entry_time)}
                  </td>
                  <td className="py-3 px-2 text-gray-900 font-mono">
                    {formatCurrency(trade.entry_price)}
                  </td>
                  <td className="py-3 px-2 text-gray-900 font-mono">
                    {formatCurrency(trade.stop_loss)}
                  </td>
                  <td className="py-3 px-2 text-gray-900 font-mono">
                    {trade.take_profit ? formatCurrency(trade.take_profit) : '-'}
                  </td>
                  <td className="py-3 px-2 text-gray-700 text-xs">
                    {formatDate(trade.exit_time)}
                  </td>
                  <td className="py-3 px-2 text-gray-900 font-mono">
                    {trade.exit_price ? formatCurrency(trade.exit_price) : '-'}
                  </td>
                  <td className="py-3 px-2">
                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                      trade.status === 'Closed Tp'
                        ? 'bg-green-100 text-green-800'
                        : trade.status === 'Closed Sl'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {trade.status}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right">
                    <div className="flex flex-col items-end">
                      <span className={`font-semibold ${
                        trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                      </span>
                      <span className={`text-xs ${
                        trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ({trade.pnl >= 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%)
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-right text-gray-900 font-medium">
                    {trade.risk_reward ? `1:${trade.risk_reward.toFixed(2)}` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-xs text-gray-600 space-y-1">
          <p><strong>SL:</strong> Stop Loss | <strong>TP:</strong> Take Profit | <strong>R:R:</strong> Risk:Reward Ratio</p>
          <p className="text-gray-500">Showing {data.length} trades total</p>
        </div>
      </CardContent>
    </Card>
  );
}
