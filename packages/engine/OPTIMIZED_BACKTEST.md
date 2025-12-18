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
   ❌ Rule 3: 23.6% Shallow Pullback
   ❌ Rule 4: Consolidation Break
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
║  Final Balance:       $21,684.70
║  Net Profit:          $11,684.70 (116.85%)
║  
║  TRADE STATISTICS
║  ───────────────────────────────────────────────────────────
║  Total Trades:        152
║  Winning Trades:      82
║  Losing Trades:       70
║  Win Rate:            53.95%
║  
║  PROFIT METRICS
║  ───────────────────────────────────────────────────────────
║  Profit Factor:       1.53
║  Average Win:         $434.88
║  Average Loss:        $333.85
║  Largest Win:         $835.27
║  Largest Loss:        $-734.37
║  Average R:R:         1.88
║  
║  RISK METRICS
║  ───────────────────────────────────────────────────────────
║  Max Drawdown:        $4869.91 (21.76%)
║  Sharpe Ratio:        3.12
╚══════════════════════════════════════════════════════════════╝


======================================================================
📋 PERFORMANCE BY RULE
======================================================================

Rule                             Trades   Win Rate   Profit Factor      Net P&L
---------------------------------------------------------------------------
Rule1_618_Golden                     66      56.1%            1.37 $   3,861.45
Rule2_786_DeepDiscount               16      25.0%            0.63 $  -1,384.12
Rule5_ATH_Retest                     44      43.2%            1.50 $   3,832.99
Rule6_50_Momentum                    26      84.6%            5.26 $   5,980.39
---------------------------------------------------------------------------

📝 Last 10 Trades:
Date                 Rule                         Dir      Entry       Exit          P&L
-------------------------------------------------------------------------------------
2025-09-15 08:00:00  Rule1_618_Golden            LONG $ 3,720.90 $ 3,868.80 $     665.78
2025-09-30 04:00:00  Rule5_ATH_Retest            LONG $ 3,843.10 $ 3,893.43 $     674.45
2025-10-02 08:00:00  Rule2_786_DeepDiscount      LONG $ 3,852.30 $ 3,930.90 $     710.01
2025-10-05 16:00:00  Rule5_ATH_Retest            LONG $ 3,935.80 $ 4,021.66 $     739.10
2025-10-09 12:00:00  Rule5_ATH_Retest            LONG $ 3,988.80 $ 4,070.54 $     766.95
2025-10-12 16:00:00  Rule5_ATH_Retest            LONG $ 4,053.60 $ 4,155.96 $     800.59
2025-10-17 12:00:00  Rule5_ATH_Retest            LONG $ 4,240.80 $ 4,371.03 $     835.27
2025-10-21 04:00:00  Rule5_ATH_Retest            LONG $ 4,267.30 $ 4,237.36 $    -448.16
2025-10-21 08:00:00  Rule6_50_Momentum           LONG $ 4,151.10 $ 4,252.73 $     429.52
2025-10-23 08:00:00  Rule1_618_Golden           SHORT $ 4,158.10 $ 4,348.80 $    -320.37

======================================================================
✅ Backtest Complete!
======================================================================
