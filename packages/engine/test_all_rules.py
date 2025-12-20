#!/usr/bin/env python3
"""
Test All Trading Rules Individually
Runs backtests on each rule separately to identify profitable ones.
"""

import sys
from pathlib import Path
import subprocess
import json

sys.path.insert(0, str(Path(__file__).parent / 'src'))

def run_rule_backtest(rule_num: str, rule_name: str):
    """Run backtest for a single rule."""
    print(f"\n{'='*80}")
    print(f"Testing {rule_name}")
    print(f"{'='*80}")

    cmd = [
        'python', 'run_backtest.py',
        '--rules', rule_num,
        '--balance', '10000',
        '--risk', '2.0'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def extract_metrics(output: str):
    """Extract key metrics from backtest output."""
    metrics = {
        'total_trades': 0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'net_profit': 0.0,
        'final_balance': 0.0,
        'sharpe_ratio': 0.0,
        'max_drawdown_pct': 0.0
    }

    lines = output.split('\n')
    for i, line in enumerate(lines):
        if 'Total Trades:' in line:
            metrics['total_trades'] = int(line.split(':')[1].strip())
        elif 'Win Rate:' in line:
            metrics['win_rate'] = float(line.split(':')[1].strip().replace('%', ''))
        elif 'Profit Factor:' in line:
            metrics['profit_factor'] = float(line.split(':')[1].strip())
        elif 'Net Profit:' in line:
            # Extract dollar amount from "Net Profit:          $14,561.53 (145.62%)"
            parts = line.split('$')
            if len(parts) > 1:
                amount = parts[1].split('(')[0].strip().replace(',', '')
                metrics['net_profit'] = float(amount)
        elif 'Final Balance:' in line:
            parts = line.split('$')
            if len(parts) > 1:
                amount = parts[1].strip().replace(',', '')
                metrics['final_balance'] = float(amount)
        elif 'Sharpe Ratio:' in line:
            metrics['sharpe_ratio'] = float(line.split(':')[1].strip())
        elif 'Max Drawdown:' in line and '%' in line:
            # Extract percentage from "Max Drawdown:        $5434.35 (21.44%)"
            pct = line.split('(')[1].split('%')[0].strip()
            metrics['max_drawdown_pct'] = float(pct)

    return metrics

def main():
    print("="*80)
    print("🧪 TESTING ALL TRADING RULES INDIVIDUALLY")
    print("="*80)

    rules = {
        # Original 3 rules
        '1': 'Rule 1: 61.8% Golden Retracement',
        '5': 'Rule 5: ATH Breakout Retest',
        '6': 'Rule 6: 50% Momentum',
        # New 6 rules
        '7': 'Rule 7: RSI Divergence',
        '8': 'Rule 8: EMA 9/21 Crossover',
        '9': 'Rule 9: London Session Breakout',
        '10': 'Rule 10: Order Block Retest',
        '11': 'Rule 11: VWAP Deviation',
        '12': 'Rule 12: Bollinger Band Squeeze',
    }

    results = {}

    for rule_num, rule_name in rules.items():
        output = run_rule_backtest(rule_num, rule_name)
        metrics = extract_metrics(output)
        results[rule_name] = metrics
        print(output)

    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY: ALL RULES PERFORMANCE")
    print("="*80)
    print(f"\n{'Rule':<40} {'Trades':>8} {'Win%':>8} {'PF':>8} {'Net P&L':>12} {'Sharpe':>8}")
    print("-"*88)

    # Sort by net profit
    sorted_rules = sorted(results.items(), key=lambda x: x[1]['net_profit'], reverse=True)

    for rule_name, metrics in sorted_rules:
        pf_str = f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] > 0 else "0.00"
        print(f"{rule_name:<40} {metrics['total_trades']:>8} "
              f"{metrics['win_rate']:>7.1f}% {pf_str:>8} "
              f"${metrics['net_profit']:>10,.0f} {metrics['sharpe_ratio']:>8.2f}")

    print("-"*88)

    # Profitable rules
    print("\n✅ PROFITABLE RULES (Profit Factor > 1.0):")
    profitable = [r for r, m in sorted_rules if m['profit_factor'] > 1.0 and m['total_trades'] > 0]
    for rule_name in profitable:
        metrics = results[rule_name]
        print(f"   • {rule_name}: ${metrics['net_profit']:,.0f} profit, "
              f"PF {metrics['profit_factor']:.2f}, {metrics['win_rate']:.1f}% win rate")

    # Unprofitable rules
    print("\n❌ UNPROFITABLE RULES (Should be removed):")
    unprofitable = [r for r, m in sorted_rules if m['profit_factor'] <= 1.0 or m['total_trades'] == 0]
    for rule_name in unprofitable:
        metrics = results[rule_name]
        if metrics['total_trades'] == 0:
            print(f"   • {rule_name}: No trades generated")
        else:
            print(f"   • {rule_name}: ${metrics['net_profit']:,.0f} profit, "
                  f"PF {metrics['profit_factor']:.2f}")

    print("\n" + "="*80)
    print("✅ Testing Complete!")
    print("="*80)

if __name__ == "__main__":
    main()
