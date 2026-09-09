"""
Per-symbol strategy registry for the /v1/settings/strategies admin listing.

Pure logic (no DB/file I/O) so it's unit-testable without a FastAPI test
client — same pattern as worker_status.py. The route in routes/settings.py
reads settings + tuned config files, then calls build_strategies_list().

See docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
"""
from typing import Any, Dict, List

# Canonical (symbol -> {rule_key: display_name}). GBPUSD and EURUSD
# deliberately share the same rule key (ForexSessionStrategy has exactly
# one rule) — enabled state for them comes from enabled_forex_symbols
# (symbol membership), not from a rule-name toggle.
STRATEGY_REGISTRY: Dict[str, Dict[str, str]] = {
    'XAUUSD': {'order_block_retest': 'Order Block Retest'},
    'GBPUSD': {'asian_range_london_breakout': 'Asian Range London Breakout'},
    'EURUSD': {'asian_range_london_breakout': 'Asian Range London Breakout'},
}


def build_strategies_list(
    enabled_strategies: List[str],
    enabled_forex_symbols: List[str],
    validation_by_symbol: Dict[str, Dict[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Args:
        enabled_strategies: the `enabled_strategies` setting's current
            value (gold's rule names — unchanged shape/meaning).
        enabled_forex_symbols: the `enabled_forex_symbols` setting's
            current value (symbol names).
        validation_by_symbol: symbol -> {rule_key: {profit_factor,
            win_rate, total_trades, net_profit_pct}}, pre-loaded by the
            caller from each symbol's tuned config file (shape differs per
            symbol — the caller normalizes it before passing in here).

    Returns:
        One entry per (symbol, rule) in STRATEGY_REGISTRY.
    """
    enabled_strategies = set(enabled_strategies or [])
    enabled_forex_symbols = set(enabled_forex_symbols or [])

    entries = []
    for symbol, rules in STRATEGY_REGISTRY.items():
        symbol_validation = validation_by_symbol.get(symbol, {})
        for rule_key, display_name in rules.items():
            if symbol == 'XAUUSD':
                enabled = rule_key in enabled_strategies
            else:
                enabled = symbol in enabled_forex_symbols

            stats = symbol_validation.get(rule_key, {})
            entries.append({
                "key": rule_key,
                "symbol": symbol,
                "name": display_name,
                "enabled": enabled,
                "validated": rule_key in symbol_validation,
                "profit_factor": stats.get('profit_factor'),
                "win_rate": stats.get('win_rate'),
                "total_trades": stats.get('total_trades'),
                "net_profit_pct": stats.get('net_profit_pct'),
            })
    return entries
