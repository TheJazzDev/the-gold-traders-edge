"""
Multi-Timeframe Comprehensive Backtest
Tests all rules across all timeframes to identify the most profitable combinations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from datetime import datetime
from data.loader import load_gold_data
from backtesting.engine import BacktestEngine
from signals.gold_strategy import GoldStrategy, create_strategy_function

# Timeframes to test
TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d']

# All rules to test
ALL_RULES = [
    'momentum_equilibrium',
    'london_session_breakout',
    'golden_fibonacci',
    'order_block_retest',
    'ath_retest',
    'bollinger_squeeze'
]

def run_backtest_for_rule(rule_name: str, timeframe: str, df: pd.DataFrame):
    """Run backtest for a single rule on a single timeframe."""
    # Enable only this rule
    strategy = GoldStrategy()
    for r in strategy.rules_enabled:
        strategy.rules_enabled[r] = False
    strategy.rules_enabled[rule_name] = True

    # Run backtest
    engine = BacktestEngine(
        initial_balance=10000,
        position_size_pct=2.0,
        commission=2.0,
        slippage=0.5
    )

    result = engine.run(
        df=df,
        strategy_func=create_strategy_function(strategy),
        max_open_trades=1
    )

    return result

def main():
    print("=" * 80)
    print("MULTI-TIMEFRAME COMPREHENSIVE BACKTEST")
    print("Testing all rules across all timeframes")
    print("=" * 80)

    # Store results
    results = []

    for timeframe in TIMEFRAMES:
        print(f"\n{'='*80}")
        print(f"TIMEFRAME: {timeframe.upper()}")
        print(f"{'='*80}")

        # Load data for this timeframe
        print(f"\n📊 Loading {timeframe} data...")
        try:
            df = load_gold_data(
                start_date="2023-01-01",
                end_date="2025-12-23",
                timeframe=timeframe
            )
            print(f"   Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        except Exception as e:
            print(f"   ❌ Error loading {timeframe} data: {e}")
            continue

        # Test each rule
        for rule_name in ALL_RULES:
            print(f"\n   Testing: {rule_name}")
            try:
                result = run_backtest_for_rule(rule_name, timeframe, df)

                # Extract key metrics
                total_trades = len(result.trades)
                wins = sum(1 for t in result.trades if t.pnl > 0)
                losses = total_trades - wins
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

                total_pnl = sum(t.pnl for t in result.trades)

                # Calculate profit factor
                total_wins = sum(t.pnl for t in result.trades if t.pnl > 0)
                total_losses = abs(sum(t.pnl for t in result.trades if t.pnl < 0))
                profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

                # Store result
                results.append({
                    'timeframe': timeframe,
                    'rule': rule_name,
                    'trades': total_trades,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'profit_factor': profit_factor,
                    'final_balance': result.final_balance
                })

                # Print summary
                status = "✅ PROFITABLE" if total_pnl > 0 else "❌ LOSING"
                print(f"      {status}")
                print(f"      Trades: {total_trades} | Win Rate: {win_rate:.1f}% | PnL: ${total_pnl:.2f} | PF: {profit_factor:.2f}")

            except Exception as e:
                print(f"      ❌ Error: {e}")
                continue

    # Create summary DataFrame
    print(f"\n\n{'='*80}")
    print("COMPREHENSIVE RESULTS SUMMARY")
    print(f"{'='*80}\n")

    results_df = pd.DataFrame(results)

    if len(results_df) == 0:
        print("❌ No results to display")
        return

    # Sort by total PnL descending
    results_df = results_df.sort_values('total_pnl', ascending=False)

    # Display top performers
    print("\n🏆 TOP 10 PROFITABLE COMBINATIONS:")
    print("-" * 80)
    top_10 = results_df.head(10)
    for idx, row in top_10.iterrows():
        if row['total_pnl'] > 0:
            print(f"{row['timeframe']:>4} | {row['rule']:<30} | "
                  f"Trades: {row['trades']:>3} | WR: {row['win_rate']:>5.1f}% | "
                  f"PnL: ${row['total_pnl']:>8.2f} | PF: {row['profit_factor']:.2f}")

    # Show worst performers
    print("\n\n📉 WORST 10 COMBINATIONS:")
    print("-" * 80)
    worst_10 = results_df.tail(10)
    for idx, row in worst_10.iterrows():
        print(f"{row['timeframe']:>4} | {row['rule']:<30} | "
              f"Trades: {row['trades']:>3} | WR: {row['win_rate']:>5.1f}% | "
              f"PnL: ${row['total_pnl']:>8.2f} | PF: {row['profit_factor']:.2f}")

    # Summary by rule (aggregated across all timeframes)
    print("\n\n📊 SUMMARY BY RULE (All Timeframes Combined):")
    print("-" * 80)
    rule_summary = results_df.groupby('rule').agg({
        'trades': 'sum',
        'wins': 'sum',
        'total_pnl': 'sum',
    }).reset_index()

    rule_summary['win_rate'] = (rule_summary['wins'] / rule_summary['trades'] * 100)
    rule_summary = rule_summary.sort_values('total_pnl', ascending=False)

    for idx, row in rule_summary.iterrows():
        status = "✅ KEEP" if row['total_pnl'] > 100 else "❌ REMOVE"
        print(f"{status} | {row['rule']:<30} | "
              f"Trades: {row['trades']:>4} | WR: {row['win_rate']:>5.1f}% | "
              f"Total PnL: ${row['total_pnl']:>9.2f}")

    # Summary by timeframe
    print("\n\n📊 SUMMARY BY TIMEFRAME (All Rules Combined):")
    print("-" * 80)
    tf_summary = results_df.groupby('timeframe').agg({
        'trades': 'sum',
        'wins': 'sum',
        'total_pnl': 'sum',
    }).reset_index()

    tf_summary['win_rate'] = (tf_summary['wins'] / tf_summary['trades'] * 100)
    tf_summary = tf_summary.sort_values('total_pnl', ascending=False)

    for idx, row in tf_summary.iterrows():
        print(f"{row['timeframe']:>4} | "
              f"Trades: {row['trades']:>4} | WR: {row['win_rate']:>5.1f}% | "
              f"Total PnL: ${row['total_pnl']:>9.2f}")

    # Save results to CSV
    output_file = Path(__file__).parent / "analysis" / "multi_timeframe_results.csv"
    output_file.parent.mkdir(exist_ok=True)
    results_df.to_csv(output_file, index=False)
    print(f"\n\n💾 Results saved to: {output_file}")

    # Recommendations
    print("\n\n🎯 RECOMMENDATIONS:")
    print("-" * 80)
    profitable_rules = rule_summary[rule_summary['total_pnl'] > 100]['rule'].tolist()
    unprofitable_rules = rule_summary[rule_summary['total_pnl'] <= 100]['rule'].tolist()

    print(f"\n✅ KEEP THESE RULES (Profitable across timeframes):")
    for rule in profitable_rules:
        print(f"   • {rule}")

    print(f"\n❌ REMOVE THESE RULES (Not profitable):")
    for rule in unprofitable_rules:
        print(f"   • {rule}")

    best_timeframes = tf_summary.head(3)['timeframe'].tolist()
    print(f"\n🎯 FOCUS ON THESE TIMEFRAMES:")
    for tf in best_timeframes:
        pnl = tf_summary[tf_summary['timeframe'] == tf]['total_pnl'].iloc[0]
        print(f"   • {tf:>4} (Total PnL: ${pnl:,.2f})")

if __name__ == "__main__":
    main()
