/Users/jazzdev/Documents/Programming/the-gold-traders-edge/packages/engine/src/data/loader.py:117: FutureWarning: In a future version of pandas, parsing datetimes with mixed time zones will raise an error unless `utc=True`. Please specify `utc=True` to opt in to the new behaviour and silence this warning. To create a `Series` with mixed offsets and `object` dtype, please use `apply` and `datetime.datetime.strptime`
  df[date_col_found] = pd.to_datetime(df[date_col_found], format=date_format)
======================================================================
🥇 THE GOLD TRADER'S EDGE - BACKTEST ENGINE
======================================================================

📊 Loading Data...
   Found real data: xauusd_4h_2023_2025.csv
Loading data from data/processed/xauusd_4h_2023_2025.csv...
Loaded 3100 candles
   Loaded 3100 candles from real data
   Date Range: 2023-12-18 04:00:00-05:00 to 2025-12-16 20:00:00-05:00
   Total Candles: 3100

🎯 Initializing Strategy...

   Active Rules:
   ✅ Rule 1: 61.8% Golden Retracement
   ✅ Rule 2: 78.6% Deep Discount
   ✅ Rule 3: 23.6% Shallow Pullback
   ✅ Rule 4: Consolidation Break
   ✅ Rule 5: ATH Breakout Retest
   ✅ Rule 6: 50% Momentum

💰 Backtest Settings:
   Initial Balance: $10,000.00
   Risk per Trade: 2.0%

🚀 Running Backtest...
----------------------------------------------------------------------
Running backtest on 3100 candles...
Period: 2023-12-18 04:00:00-05:00 to 2025-12-16 20:00:00-05:00

╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Period: 2023-12-18 to 2025-12-16
║  
║  PERFORMANCE
║  ───────────────────────────────────────────────────────────
║  Initial Balance:     $10,000.00
║  Final Balance:       $21,199.53
║  Net Profit:          $11,199.53 (112.00%)
║  
║  TRADE STATISTICS
║  ───────────────────────────────────────────────────────────
║  Total Trades:        147
║  Winning Trades:      80
║  Losing Trades:       67
║  Win Rate:            54.42%
║  
║  PROFIT METRICS
║  ───────────────────────────────────────────────────────────
║  Profit Factor:       1.56
║  Average Win:         $410.52
║  Average Loss:        $314.27
║  Largest Win:         $816.59
║  Largest Loss:        $-717.99
║  Average R:R:         1.91
║  
║  RISK METRICS
║  ───────────────────────────────────────────────────────────
║  Max Drawdown:        $3985.47 (18.22%)
║  Sharpe Ratio:        3.25
╚══════════════════════════════════════════════════════════════╝


======================================================================
📋 PERFORMANCE BY RULE
======================================================================

Rule                             Trades   Win Rate   Profit Factor      Net P&L
---------------------------------------------------------------------------
Rule1_618_Golden                     57      50.9%            1.14 $   1,355.55
Rule2_786_DeepDiscount               15      40.0%            1.31 $     816.35
Rule3_236_Shallow                     3       0.0%            0.00 $    -866.20
Rule4_ConsolidationBreak              5      20.0%            0.64 $    -388.46
Rule5_ATH_Retest                     32      43.8%            1.64 $   3,367.41
Rule6_50_Momentum                    35      85.7%            5.82 $   7,500.89
---------------------------------------------------------------------------

📝 Last 10 Trades:
Date                 Rule                         Dir      Entry       Exit          P&L
-------------------------------------------------------------------------------------
2025-09-15 08:00:00  Rule1_618_Golden            LONG $ 3,720.90 $ 3,868.80 $     650.91
2025-09-30 04:00:00  Rule5_ATH_Retest            LONG $ 3,843.10 $ 3,893.43 $     659.39
2025-10-02 08:00:00  Rule2_786_DeepDiscount      LONG $ 3,852.30 $ 3,930.90 $     694.14
2025-10-05 16:00:00  Rule5_ATH_Retest            LONG $ 3,935.80 $ 4,021.66 $     722.58
2025-10-09 12:00:00  Rule5_ATH_Retest            LONG $ 3,988.80 $ 4,070.54 $     749.81
2025-10-12 16:00:00  Rule5_ATH_Retest            LONG $ 4,053.60 $ 4,155.96 $     782.69
2025-10-17 12:00:00  Rule5_ATH_Retest            LONG $ 4,240.80 $ 4,371.03 $     816.59
2025-10-21 04:00:00  Rule5_ATH_Retest            LONG $ 4,267.30 $ 4,237.36 $    -438.14
2025-10-21 08:00:00  Rule6_50_Momentum           LONG $ 4,151.10 $ 4,252.73 $     419.91
2025-10-23 08:00:00  Rule1_618_Golden           SHORT $ 4,158.10 $ 4,348.80 $    -313.20

======================================================================
✅ Backtest Complete!
======================================================================
