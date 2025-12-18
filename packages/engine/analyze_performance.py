#!/usr/bin/env python3
"""
Performance Analysis Script
Analyzes backtest results and generates comprehensive performance reports with visualizations.

Usage:
    python analyze_performance.py --data data.csv              # Analyze specific dataset
    python analyze_performance.py --timeframe 4h               # Analyze 4h data
    python analyze_performance.py --compare 4h,1d              # Compare timeframes
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze Backtest Performance')
    parser.add_argument('--data', type=str, help='Path to CSV data file')
    parser.add_argument('--timeframe', type=str, default='4h', help='Timeframe to analyze (4h, 1d)')
    parser.add_argument('--compare', type=str, help='Compare multiple timeframes (e.g., 4h,1d)')
    parser.add_argument('--rules', type=str, help='Comma-separated rule numbers (e.g., 1,2,5,6)')
    parser.add_argument('--output-dir', type=str, default='analysis', help='Output directory for reports')
    return parser.parse_args()


def run_backtest(df, rules=None):
    """Run backtest and return results."""
    strategy = GoldStrategy()

    # Enable/disable specific rules
    if rules:
        for rule in strategy.rules_enabled:
            strategy.rules_enabled[rule] = False

        rule_map = {
            '1': 'rule_1_618_retracement',
            '2': 'rule_2_786_deep_discount',
            '3': 'rule_3_236_shallow_pullback',
            '4': 'rule_4_consolidation_break',
            '5': 'rule_5_ath_breakout_retest',
            '6': 'rule_6_50_momentum',
        }

        for rule_num in rules.split(','):
            rule_num = rule_num.strip()
            if rule_num in rule_map:
                strategy.rules_enabled[rule_map[rule_num]] = True

    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    result = engine.run(df=df, strategy_func=create_strategy_function(strategy))

    return result


def analyze_equity_curve(result, output_dir):
    """Plot equity curve over time."""
    if not result.trades:
        print("No trades to analyze.")
        return

    # Build equity curve
    equity = [result.initial_balance]
    dates = [result.start_date]

    for trade in result.trades:
        equity.append(equity[-1] + trade.pnl)
        dates.append(trade.exit_time)

    # Plot
    plt.figure(figsize=(14, 7))
    plt.plot(dates, equity, linewidth=2, color='#2E86AB')
    plt.fill_between(dates, result.initial_balance, equity, alpha=0.3, color='#2E86AB')

    plt.axhline(y=result.initial_balance, color='gray', linestyle='--', alpha=0.5, label='Initial Balance')
    plt.title('Equity Curve', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Account Balance ($)', fontsize=12)
    plt.grid(alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    filepath = output_dir / 'equity_curve.png'
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: {filepath}")


def analyze_drawdown(result, output_dir):
    """Plot drawdown chart."""
    if not result.trades:
        return

    # Calculate drawdown
    equity = [result.initial_balance]
    for trade in result.trades:
        equity.append(equity[-1] + trade.pnl)

    equity = pd.Series(equity)
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max * 100

    dates = [result.start_date] + [t.exit_time for t in result.trades]

    # Plot
    plt.figure(figsize=(14, 6))
    plt.fill_between(dates, 0, drawdown.values, alpha=0.5, color='red')
    plt.plot(dates, drawdown.values, color='darkred', linewidth=2)

    plt.title('Drawdown', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Drawdown (%)', fontsize=12)
    plt.grid(alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    filepath = output_dir / 'drawdown.png'
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: {filepath}")


def analyze_rule_performance(result, output_dir):
    """Analyze and plot performance by rule."""
    if not result.trades:
        return

    rule_stats = {}
    for trade in result.trades:
        rule = trade.signal_name
        if rule not in rule_stats:
            rule_stats[rule] = {'count': 0, 'wins': 0, 'pnl': 0}

        rule_stats[rule]['count'] += 1
        rule_stats[rule]['pnl'] += trade.pnl
        if trade.pnl > 0:
            rule_stats[rule]['wins'] += 1

    # Sort by PnL
    rules = sorted(rule_stats.keys(), key=lambda r: rule_stats[r]['pnl'], reverse=True)
    pnls = [rule_stats[r]['pnl'] for r in rules]
    win_rates = [(rule_stats[r]['wins'] / rule_stats[r]['count'] * 100) for r in rules]

    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # PnL by rule
    colors = ['green' if p > 0 else 'red' for p in pnls]
    ax1.barh(rules, pnls, color=colors, alpha=0.7)
    ax1.set_xlabel('Net P&L ($)', fontsize=12)
    ax1.set_title('Net P&L by Rule', fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    ax1.axvline(x=0, color='black', linewidth=0.8)

    # Win rate by rule
    ax2.barh(rules, win_rates, color='#2E86AB', alpha=0.7)
    ax2.set_xlabel('Win Rate (%)', fontsize=12)
    ax2.set_title('Win Rate by Rule', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    ax2.axvline(x=50, color='orange', linewidth=0.8, linestyle='--', label='50%')
    ax2.legend()

    plt.tight_layout()
    filepath = output_dir / 'rule_performance.png'
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: {filepath}")


def analyze_trade_distribution(result, output_dir):
    """Plot trade P&L distribution."""
    if not result.trades:
        return

    pnls = [t.pnl for t in result.trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Histogram
    ax1.hist(pnls, bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax1.axvline(x=0, color='red', linewidth=2, linestyle='--')
    ax1.set_xlabel('P&L ($)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Trade P&L Distribution', fontsize=14, fontweight='bold')
    ax1.grid(alpha=0.3)

    # Win/Loss comparison
    data = [wins, losses]
    labels = [f'Wins\n({len(wins)})', f'Losses\n({len(losses)})']
    colors = ['green', 'red']

    bp = ax2.boxplot(data, labels=labels, patch_artist=True, showmeans=True)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    ax2.set_ylabel('P&L ($)', fontsize=12)
    ax2.set_title('Win vs Loss Comparison', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.8)

    plt.tight_layout()
    filepath = output_dir / 'trade_distribution.png'
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: {filepath}")


def generate_report(result, timeframe, output_dir):
    """Generate comprehensive text report."""
    report = []
    report.append("=" * 80)
    report.append("COMPREHENSIVE PERFORMANCE ANALYSIS")
    report.append("=" * 80)
    report.append(f"\nTimeframe: {timeframe}")
    report.append(f"Period: {result.start_date} to {result.end_date}")
    report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate derived metrics
    net_profit = result.final_balance - result.initial_balance
    return_pct = (net_profit / result.initial_balance) * 100

    report.append("\n\n" + "=" * 80)
    report.append("PERFORMANCE METRICS")
    report.append("=" * 80)
    report.append(f"\nInitial Balance:      ${result.initial_balance:,.2f}")
    report.append(f"Final Balance:        ${result.final_balance:,.2f}")
    report.append(f"Net Profit:           ${net_profit:,.2f} ({return_pct:.2f}%)")
    report.append(f"\nTotal Trades:         {result.total_trades}")
    report.append(f"Winning Trades:       {result.winning_trades}")
    report.append(f"Losing Trades:        {result.losing_trades}")
    report.append(f"Win Rate:             {result.win_rate:.2f}%")
    report.append(f"\nProfit Factor:        {result.profit_factor:.2f}")
    report.append(f"Average Win:          ${result.avg_win:.2f}")
    report.append(f"Average Loss:         ${result.avg_loss:.2f}")
    report.append(f"Average R:R:          {result.avg_rr:.2f}")
    report.append(f"\nMax Drawdown:         ${result.max_drawdown:.2f} ({result.max_drawdown_pct:.2f}%)")
    report.append(f"Sharpe Ratio:         {result.sharpe_ratio:.2f}")

    # Rule breakdown
    if result.trades:
        report.append("\n\n" + "=" * 80)
        report.append("RULE PERFORMANCE")
        report.append("=" * 80)

        rule_stats = {}
        for trade in result.trades:
            rule = trade.signal_name
            if rule not in rule_stats:
                rule_stats[rule] = {
                    'count': 0, 'wins': 0, 'losses': 0,
                    'gross_profit': 0, 'gross_loss': 0, 'pnl': 0
                }

            rule_stats[rule]['count'] += 1
            rule_stats[rule]['pnl'] += trade.pnl

            if trade.pnl > 0:
                rule_stats[rule]['wins'] += 1
                rule_stats[rule]['gross_profit'] += trade.pnl
            else:
                rule_stats[rule]['losses'] += 1
                rule_stats[rule]['gross_loss'] += abs(trade.pnl)

        report.append(f"\n{'Rule':<30} {'Trades':>8} {'Win Rate':>10} {'PF':>8} {'Net P&L':>12}")
        report.append("-" * 80)

        for rule, stats in sorted(rule_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            pf = stats['gross_profit'] / stats['gross_loss'] if stats['gross_loss'] > 0 else float('inf')
            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"

            report.append(f"{rule:<30} {stats['count']:>8} {win_rate:>9.1f}% {pf_str:>8} ${stats['pnl']:>11,.2f}")

    # Trading insights
    report.append("\n\n" + "=" * 80)
    report.append("KEY INSIGHTS")
    report.append("=" * 80)

    if return_pct > 50:
        report.append("\n✅ Excellent overall performance!")
    elif return_pct > 20:
        report.append("\n✅ Good overall performance.")
    else:
        report.append("\n⚠️  Moderate performance - consider optimization.")

    if result.win_rate > 55:
        report.append("✅ Strong win rate - strategy is consistent.")
    elif result.win_rate > 45:
        report.append("⚠️  Moderate win rate - could be improved.")
    else:
        report.append("❌ Low win rate - review entry/exit rules.")

    if result.profit_factor > 2.0:
        report.append("✅ Excellent profit factor - wins significantly outweigh losses.")
    elif result.profit_factor > 1.5:
        report.append("✅ Good profit factor - strategy is profitable.")
    elif result.profit_factor > 1.0:
        report.append("⚠️  Marginal profit factor - needs improvement.")
    else:
        report.append("❌ Poor profit factor - strategy is losing money.")

    if result.max_drawdown_pct < 15:
        report.append("✅ Excellent risk management - low drawdown.")
    elif result.max_drawdown_pct < 25:
        report.append("⚠️  Moderate drawdown - acceptable but could be better.")
    else:
        report.append("❌ High drawdown - improve risk management.")

    if result.sharpe_ratio > 3:
        report.append("✅ Exceptional risk-adjusted returns (Sharpe > 3).")
    elif result.sharpe_ratio > 2:
        report.append("✅ Excellent risk-adjusted returns (Sharpe > 2).")
    elif result.sharpe_ratio > 1:
        report.append("⚠️  Good risk-adjusted returns (Sharpe > 1).")
    else:
        report.append("❌ Poor risk-adjusted returns - strategy is risky.")

    report.append("\n\n" + "=" * 80)

    # Save report
    filepath = output_dir / 'analysis_report.txt'
    with open(filepath, 'w') as f:
        f.write('\n'.join(report))

    print(f"\n   Saved: {filepath}")

    # Also print to console
    print('\n'.join(report))


def main():
    args = parse_args()

    print("=" * 80)
    print("📊 PERFORMANCE ANALYSIS")
    print("=" * 80)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    loader = GoldDataLoader()

    if args.data:
        df = loader.load_from_csv(args.data)
        timeframe = args.timeframe
    else:
        # Auto-detect
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{args.timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            print(f"❌ No data found for {args.timeframe}")
            print(f"Run: python fetch_real_data.py --timeframe {args.timeframe}")
            sys.exit(1)

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))
        timeframe = args.timeframe

    print(f"\n📈 Analyzing {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    # Run backtest
    print(f"\n🚀 Running backtest...")
    result = run_backtest(df, args.rules)

    # Generate visualizations
    print(f"\n📊 Generating visualizations...")
    analyze_equity_curve(result, output_dir)
    analyze_drawdown(result, output_dir)
    analyze_rule_performance(result, output_dir)
    analyze_trade_distribution(result, output_dir)

    # Generate report
    print(f"\n📝 Generating report...")
    generate_report(result, timeframe, output_dir)

    print("\n" + "=" * 80)
    print(f"✅ ANALYSIS COMPLETE! Check the '{args.output_dir}' directory for results.")
    print("=" * 80)


if __name__ == "__main__":
    main()
