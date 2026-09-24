"""
Telegram message bodies (HTML parse mode), kept apart from the sending
logic in telegram_subscriber.py. All pip/price/dollar math goes through
`instruments`, so a forex signal is never rendered with gold's pip size.
"""

from typing import Optional

from instruments import format_price, lot_size_pnl, price_to_pips


def _money(value: float) -> str:
    return f"{'+' if value >= 0 else '-'}${abs(value):,.2f}"


def _lot_line(lots: float) -> str:
    return f"{lots:.2f} lot"


def format_signal_message(signal) -> str:
    """New-signal message. `signal` is a ValidatedSignal (or anything with
    the same attributes)."""
    symbol = signal.symbol
    direction_emoji = "🟢" if signal.direction == "LONG" else "🔴"
    arrow = "📈" if signal.direction == "LONG" else "📉"
    confidence_stars = "⭐" * int(signal.confidence * 5)

    risk_distance = abs(signal.entry_price - signal.stop_loss)
    reward_distance = abs(signal.take_profit - signal.entry_price)
    risk_pips = price_to_pips(symbol, risk_distance)
    reward_pips = price_to_pips(symbol, reward_distance)

    risk_rows = lot_size_pnl(symbol, -risk_distance)
    reward_rows = lot_size_pnl(symbol, reward_distance)
    lot_rows = "\n".join(
        f"├ {_lot_line(lots)}: {_money(risk)} / {_money(reward)}"
        for (lots, risk), (_, reward) in zip(risk_rows, reward_rows)
    )

    time_str = signal.timestamp.strftime("%Y-%m-%d %H:%M UTC")
    reference_id = getattr(signal, "reference_id", None)
    id_line = f"<b>ID:</b> {reference_id}\n" if reference_id else ""

    return f"""
{direction_emoji} <b>NEW {signal.direction} SIGNAL</b> {arrow}

{id_line}<b>Symbol:</b> {symbol}
<b>Strategy:</b> {signal.strategy_name}
<b>Timeframe:</b> {signal.timeframe}
<b>Time:</b> {time_str}

💰 <b>TRADE DETAILS</b>
├ Entry: {format_price(symbol, signal.entry_price)}
├ Stop Loss: {format_price(symbol, signal.stop_loss)}
├ Take Profit: {format_price(symbol, signal.take_profit)}

📊 <b>RISK MANAGEMENT</b>
├ Risk: {risk_pips:.1f} pips
├ Reward: {reward_pips:.1f} pips
├ R:R Ratio: 1:{signal.risk_reward_ratio:.2f}
├ Confidence: {signal.confidence:.0%} {confidence_stars}

💵 <b>RISK / REWARD BY LOT SIZE</b>
{lot_rows}

{signal.notes or ""}
""".strip()


def format_close_message(
    *,
    reference_id: Optional[str],
    symbol: str,
    direction: str,
    strategy_name: str,
    entry_price: float,
    exit_price: Optional[float],
    outcome: str,
    r_multiple: Optional[float],
) -> str:
    """Resolution message (TP hit, SL hit, or expired with no resolution).
    outcome: "closed_tp", "closed_sl", or "expired"."""
    label = reference_id or "this signal"

    if outcome == "closed_tp":
        headline = f"✅ <b>TAKE PROFIT HIT</b> — {label}"
    elif outcome == "closed_sl":
        headline = f"❌ <b>STOP LOSS HIT</b> — {label}"
    else:
        headline = f"⌛ <b>EXPIRED (no resolution)</b> — {label}"

    exit_line = ""
    pnl_block = ""
    if exit_price is not None:
        move = exit_price - entry_price
        if direction != "LONG":
            move = -move
        exit_line = (
            f"├ Exit: {format_price(symbol, exit_price)}\n"
            f"├ Pips: {price_to_pips(symbol, move):+.1f} pips\n"
        )
        lot_rows = "\n".join(
            f"├ {_lot_line(lots)}: {_money(pnl)}"
            for lots, pnl in lot_size_pnl(symbol, move)
        )
        pnl_block = f"\n\n💵 <b>P&amp;L BY LOT SIZE</b>\n{lot_rows}"

    result_line = f"Result: {r_multiple:+.2f}R" if r_multiple is not None else ""

    return f"""
{headline}

<b>Symbol:</b> {symbol} {direction}
<b>Strategy:</b> {strategy_name}

├ Entry: {format_price(symbol, entry_price)}
{exit_line}{result_line}{pnl_block}
""".strip()
