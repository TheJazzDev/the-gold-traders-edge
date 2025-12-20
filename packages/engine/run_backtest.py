#!/usr/bin/env python3
"""
Gold Strategy Backtest Runner
Run backtests on profitable gold trading strategies.

Usage:
    python run_backtest.py                              # Run default (momentum + london)
    python run_backtest.py --data path.csv              # Run with custom data
    python run_backtest.py --rules momentum             # Test Momentum Equilibrium only
    python run_backtest.py --rules momentum,london      # Test multiple strategies
    python run_backtest.py --rules fibonacci,orderblock # Test marginal strategies

Available strategies:
    momentum, equilibrium     - Momentum Equilibrium (74% win rate) ⭐ STAR PERFORMER
    london                    - London Session Breakout (58.8% win rate)
    fibonacci, golden         - Golden Fibonacci 61.8% (49% win rate)
    orderblock                - Order Block Retest (38.6% win rate)
    ath                       - ATH/ATL Retest (barely profitable)
    bollinger                 - Bollinger Squeeze (barely profitable)
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader, generate_sample_data
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine


def parse_args():
    parser = argparse.ArgumentParser(description='Run Gold Strategy Backtest')
    parser.add_argument('--data', type=str, help='Path to CSV data file')
    parser.add_argument('--start', type=str, default='2022-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-01', help='End date (YYYY-MM-DD)')
    parser.add_argument('--timeframe', type=str, default='4h', help='Timeframe (1h, 4h, 1D)')
    parser.add_argument('--balance', type=float, default=10000, help='Initial balance')
    parser.add_argument('--risk', type=float, default=2.0, help='Risk per trade (%%)')
    parser.add_argument('--rules', type=str, help='Comma-separated rule names (e.g., momentum,london,fibonacci)')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 70)
    print("🥇 THE GOLD TRADER'S EDGE - BACKTEST ENGINE")
    print("=" * 70)
    
    # Load data
    print("\n📊 Loading Data...")

    loader = GoldDataLoader()

    if args.data:
        # User specified a data file
        df = loader.load_from_csv(args.data)
        print(f"   Loaded {len(df)} candles from {args.data}")
    else:
        # Try to auto-detect real data files
        processed_dir = Path("data/processed")

        # Look for matching timeframe files
        if processed_dir.exists():
            pattern = f"xauusd_{args.timeframe}_*.csv"
            matching_files = list(processed_dir.glob(pattern))

            if matching_files:
                # Use the most recent file (sorted by name, which includes year)
                data_file = sorted(matching_files)[-1]
                print(f"   Found real data: {data_file.name}")
                df = loader.load_from_csv(str(data_file))
                print(f"   Loaded {len(df)} candles from real data")
            else:
                print(f"   ⚠️  No real data found for {args.timeframe} timeframe")
                print(f"   Run: python fetch_real_data.py --timeframe {args.timeframe}")
                print(f"\n   Falling back to synthetic data...")
                df = generate_sample_data(
                    start_date=args.start,
                    end_date=args.end,
                    timeframe=args.timeframe
                )
        else:
            print(f"   ⚠️  No real data available")
            print(f"   Run: python fetch_real_data.py --timeframe {args.timeframe}")
            print(f"\n   Falling back to synthetic data...")
            df = generate_sample_data(
                start_date=args.start,
                end_date=args.end,
                timeframe=args.timeframe
            )
    
    print(f"   Date Range: {df.index[0]} to {df.index[-1]}")
    print(f"   Total Candles: {len(df)}")
    
    # Initialize strategy
    print("\n🎯 Initializing Strategy...")
    strategy = GoldStrategy()
    
    # Enable/disable specific rules if specified
    if args.rules:
        # Disable all first
        for rule in strategy.rules_enabled:
            strategy.rules_enabled[rule] = False
        
        # Enable specified rules by name
        rule_map = {
            # STAR PERFORMER
            'momentum': 'momentum_equilibrium',
            'equilibrium': 'momentum_equilibrium',
            # STRONG PERFORMER
            'london': 'london_session_breakout',
            # MARGINAL (disabled by default)
            'fibonacci': 'golden_fibonacci',
            'golden': 'golden_fibonacci',
            'orderblock': 'order_block_retest',
            'ath': 'ath_retest',
            'bollinger': 'bollinger_squeeze',
        }

        for rule_name in args.rules.split(','):
            rule_name = rule_name.strip().lower()
            if rule_name in rule_map:
                strategy.rules_enabled[rule_map[rule_name]] = True

    print("\n   Active Rules:")
    rule_names = {
        'momentum_equilibrium': 'Momentum Equilibrium (50% Fib) ⭐',
        'london_session_breakout': 'London Session Breakout',
        'golden_fibonacci': 'Golden Fibonacci (61.8%)',
        'order_block_retest': 'Order Block Retest',
        'ath_retest': 'ATH/ATL Retest',
        'bollinger_squeeze': 'Bollinger Band Squeeze',
    }
    
    for rule, enabled in strategy.rules_enabled.items():
        status = "✅" if enabled else "❌"
        name = rule_names.get(rule, rule)
        print(f"   {status} {name}")
    
    # Initialize backtest engine
    print(f"\n💰 Backtest Settings:")
    print(f"   Initial Balance: ${args.balance:,.2f}")
    print(f"   Risk per Trade: {args.risk}%")
    
    engine = BacktestEngine(
        initial_balance=args.balance,
        position_size_pct=args.risk,
        commission=2.0,
        slippage=0.5
    )
    
    # Run backtest
    print("\n🚀 Running Backtest...")
    print("-" * 70)
    
    result = engine.run(
        df=df,
        strategy_func=create_strategy_function(strategy),
        max_open_trades=1
    )
    
    # Display results
    print(result.summary())
    
    # Breakdown by rule
    if result.trades:
        print("\n" + "=" * 70)
        print("📋 PERFORMANCE BY RULE")
        print("=" * 70)
        
        rule_stats = {}
        for trade in result.trades:
            rule = trade.signal_name
            if rule not in rule_stats:
                rule_stats[rule] = {
                    'count': 0, 
                    'wins': 0, 
                    'losses': 0,
                    'gross_profit': 0,
                    'gross_loss': 0,
                    'pnl': 0
                }
            
            rule_stats[rule]['count'] += 1
            rule_stats[rule]['pnl'] += trade.pnl
            
            if trade.pnl > 0:
                rule_stats[rule]['wins'] += 1
                rule_stats[rule]['gross_profit'] += trade.pnl
            else:
                rule_stats[rule]['losses'] += 1
                rule_stats[rule]['gross_loss'] += abs(trade.pnl)
        
        print(f"\n{'Rule':<30} {'Trades':>8} {'Win Rate':>10} {'Profit Factor':>15} {'Net P&L':>12}")
        print("-" * 75)
        
        for rule, stats in sorted(rule_stats.items()):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            pf = stats['gross_profit'] / stats['gross_loss'] if stats['gross_loss'] > 0 else float('inf')
            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
            
            print(f"{rule:<30} {stats['count']:>8} {win_rate:>9.1f}% {pf_str:>15} ${stats['pnl']:>11,.2f}")
        
        print("-" * 75)
        
        # Recent trades
        print("\n📝 Last 10 Trades:")
        print(f"{'Date':<20} {'Rule':<25} {'Dir':>6} {'Entry':>10} {'Exit':>10} {'P&L':>12}")
        print("-" * 85)
        
        for trade in result.trades[-10:]:
            direction = "LONG" if trade.direction.value == "long" else "SHORT"
            exit_price = trade.exit_price if trade.exit_price else 0
            print(f"{str(trade.entry_time)[:19]:<20} {trade.signal_name:<25} {direction:>6} "
                  f"${trade.entry_price:>9,.2f} ${exit_price:>9,.2f} ${trade.pnl:>11,.2f}")
    
    # Export results
    if args.output:
        result.export_to_json(args.output)
        print(f"\n💾 Results exported to: {args.output}")
    
    print("\n" + "=" * 70)
    print("✅ Backtest Complete!")
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    main()
