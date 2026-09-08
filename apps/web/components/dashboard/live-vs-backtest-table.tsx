"use client";

import type { RulePerformance, StrategyPerformance } from "@/lib/types";
import { formatProfitFactor } from "@/lib/utils";

interface LiveVsBacktestTableProps {
  live: RulePerformance[];
  backtest: StrategyPerformance[];
  loading?: boolean;
}

// Below this many closed live trades, a live win rate is mostly noise —
// see the backtested order_block_retest baseline (114 trades) for how much
// sample size it actually took to trust a number.
const MIN_TRADES_FOR_SIGNAL = 20;

export function LiveVsBacktestTable({ live, backtest, loading }: LiveVsBacktestTableProps) {
  if (loading) {
    return <div className="h-48 sm:h-56 glass rounded-xl animate-pulse" />;
  }

  const validated = backtest.filter((b) => b.validated);
  if (validated.length === 0) {
    return null;
  }

  return (
    <div className="glass rounded-xl p-4 sm:p-6">
      <div className="mb-4 sm:mb-6">
        <h3 className="text-base sm:text-xl font-bold text-white">Live vs Backtested</h3>
        <p className="text-xs sm:text-sm text-white/60 mt-1">
          Is the real edge holding up, or was it a backtest artifact?
        </p>
      </div>

      <div className="overflow-x-auto -mx-4 sm:mx-0">
        <table className="w-full text-xs sm:text-sm min-w-[480px]">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/10">
              <th className="py-2 px-4 sm:px-2 font-medium">Strategy</th>
              <th className="py-2 px-2 font-medium text-right">Backtest WR / PF (n)</th>
              <th className="py-2 px-2 font-medium text-right">Live WR / PF (n)</th>
            </tr>
          </thead>
          <tbody>
            {validated.map((baseline) => {
              const liveStats = live.find((r) => r.strategy_name === baseline.name);
              const liveClosed = liveStats?.closed_signals ?? 0;
              const hasEnoughLiveData = liveClosed >= MIN_TRADES_FOR_SIGNAL;

              return (
                <tr key={baseline.key} className="border-b border-white/5 last:border-0">
                  <td className="py-3 px-4 sm:px-2 text-white font-medium">{baseline.name}</td>
                  <td className="py-3 px-2 text-right text-white/70">
                    {baseline.win_rate?.toFixed(1)}% / {formatProfitFactor(baseline.profit_factor)}
                    <span className="text-white/40"> (n={baseline.total_trades})</span>
                  </td>
                  <td className="py-3 px-2 text-right">
                    {liveClosed > 0 ? (
                      <span className={hasEnoughLiveData ? "text-white" : "text-white/50"}>
                        {liveStats!.win_rate.toFixed(1)}% / {formatProfitFactor(liveStats!.profit_factor)}
                        <span className="text-white/40"> (n={liveClosed})</span>
                      </span>
                    ) : (
                      <span className="text-white/30">no closed trades yet</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] sm:text-xs text-white/40 mt-3">
        Live numbers are directional noise below {MIN_TRADES_FOR_SIGNAL} closed trades — the backtest baseline took{" "}
        {validated.reduce((max, b) => Math.max(max, b.total_trades ?? 0), 0)} trades to trust.
      </p>
    </div>
  );
}
