#!/usr/bin/env python3
"""
On-demand signal performance report.

Usage:
    python report.py                    # last 7 days
    python report.py --days 30
    python report.py --timeframe 1h
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from database.signal_repository import SignalRepository


def build_report_text(stats: dict, days: int) -> str:
    """Format a performance stats dict (from get_performance_stats) as text."""
    return (
        f"📊 Signal Performance Report ({days}d)\n"
        f"Total signals: {stats['total_signals']}\n"
        f"TP hits: {stats['tp_hits']}\n"
        f"SL hits: {stats['sl_hits']}\n"
        f"Expired: {stats['expired']}\n"
        f"Still open: {stats['still_open']}\n"
        f"Win rate: {stats['win_rate']:.1f}%\n"
        f"Avg R-multiple: {stats['avg_r_multiple']:.2f}\n"
        f"Net R-multiple: {stats['net_r_multiple']:.2f}"
    )


def main():
    parser = argparse.ArgumentParser(description="Gold Trader's Edge - Signal Performance Report")
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    parser.add_argument('--symbol', type=str, default=None)
    parser.add_argument('--timeframe', type=str, default=None)
    args = parser.parse_args()

    db_manager = DatabaseManager()
    with db_manager.session_scope() as session:
        repo = SignalRepository(session)
        stats = repo.get_performance_stats(days=args.days, symbol=args.symbol, timeframe=args.timeframe)

    print(build_report_text(stats, args.days))


if __name__ == "__main__":
    main()
