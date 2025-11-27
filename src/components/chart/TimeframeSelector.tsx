"use client";

import { useChartStore } from "@/store";
import type { TimeFrame } from "@/types";
import { cn } from "@/lib/utils";

const timeframes: { value: TimeFrame; label: string }[] = [
  { value: "1m", label: "1m" },
  { value: "5m", label: "5m" },
  { value: "15m", label: "15m" },
  { value: "1h", label: "1H" },
  { value: "4h", label: "4H" },
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
];

export function TimeframeSelector() {
  const { timeframe, setTimeframe } = useChartStore();

  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-secondary-900/50 border border-secondary-700/50">
      {timeframes.map((tf) => (
        <button
          key={tf.value}
          onClick={() => setTimeframe(tf.value)}
          className={cn(
            "px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
            timeframe === tf.value
              ? "bg-primary-500 text-secondary-950"
              : "text-secondary-300 hover:text-white hover:bg-secondary-800"
          )}
        >
          {tf.label}
        </button>
      ))}
    </div>
  );
}
