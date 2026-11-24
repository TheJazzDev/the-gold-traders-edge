import { format } from "date-fns";
import { formatMoney, formatPrice, formatR, parseApiDate } from "@/lib/utils";
import type { BrokerFill } from "@/lib/types";

interface BrokerFillPanelProps {
  symbol: string;
  fill: BrokerFill;
}

const CLOSE_REASON_LABEL: Record<string, string> = {
  sl: "Stop loss",
  tp: "Take profit",
  manual: "Closed by hand",
  other: "Other",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="text-gray-400 block">{label}</span>
      <span className="font-semibold text-white">{children}</span>
    </div>
  );
}

function resultTone(value: number | null) {
  if (value == null) return "text-white";
  return value >= 0 ? "text-green-400" : "text-red-400";
}

/** The real order at the broker, shown next to the paper outcome so the two
 * can be compared. The paper numbers above come from candles, not from here. */
export function BrokerFillPanel({ symbol, fill }: BrokerFillPanelProps) {
  const isOpen = fill.closed_at == null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 sm:p-4 space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h4 className="text-xs sm:text-sm font-semibold text-amber-300">Broker order</h4>
        <span className="text-[10px] sm:text-xs text-gray-400">
          Ticket {fill.ticket} · {fill.lots} lots
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:gap-4 text-xs sm:text-sm">
        <Field label="Filled at">{formatPrice(symbol, fill.entry_price)}</Field>
        <Field label="Exit price">
          {fill.exit_price != null ? formatPrice(symbol, fill.exit_price) : "Still open"}
        </Field>
        <Field label="Stop loss">{formatPrice(symbol, fill.stop_loss)}</Field>
        <Field label="Take profit">{formatPrice(symbol, fill.take_profit)}</Field>
        <div>
          <span className="text-gray-400 block">Result</span>
          <span className={`font-semibold ${resultTone(fill.profit)}`}>
            {fill.profit != null ? formatMoney(fill.profit) : "—"}
            {fill.r_multiple != null && (
              <span className="text-gray-400 font-normal"> ({formatR(fill.r_multiple)})</span>
            )}
          </span>
        </div>
        <Field label="Closed by">
          {isOpen ? "—" : (CLOSE_REASON_LABEL[fill.close_reason ?? ""] ?? fill.close_reason ?? "—")}
        </Field>
        <Field label="Opened">{format(parseApiDate(fill.opened_at), "MMM d, yyyy 'at' HH:mm")}</Field>
        <Field label="Closed">
          {fill.closed_at ? format(parseApiDate(fill.closed_at), "MMM d, yyyy 'at' HH:mm") : "—"}
        </Field>
      </div>
    </div>
  );
}
