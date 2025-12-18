/Users/jazzdev/Documents/Programming/the-gold-traders-edge/packages/engine/src/data/loader.py:117: FutureWarning: In a future version of pandas, parsing datetimes with mixed time zones will raise an error unless `utc=True`. Please specify `utc=True` to opt in to the new behaviour and silence this warning. To create a `Series` with mixed offsets and `object` dtype, please use `apply` and `datetime.datetime.strptime`
  df[date_col_found] = pd.to_datetime(df[date_col_found], format=date_format)
======================================================================
🥇 THE GOLD TRADER'S EDGE - BACKTEST ENGINE
======================================================================

📊 Loading Data...
   Found real data: xauusd_1d_2020_2025.csv
Loading data from data/processed/xauusd_1d_2020_2025.csv...
Loaded 1255 candles
   Loaded 1255 candles from real data
   Date Range: 2020-12-21 00:00:00-05:00 to 2025-12-16 00:00:00-05:00
   Total Candles: 1255

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
Running backtest on 1255 candles...
Period: 2020-12-21 00:00:00-05:00 to 2025-12-16 00:00:00-05:00

╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Period: 2020-12-21 to 2025-12-16
║  
║  PERFORMANCE
║  ───────────────────────────────────────────────────────────
║  Initial Balance:     $10,000.00
║  Final Balance:       $15,347.57
║  Net Profit:          $5,347.57 (53.48%)
║  
║  TRADE STATISTICS
║  ───────────────────────────────────────────────────────────
║  Total Trades:        59
║  Winning Trades:      34
║  Losing Trades:       25
║  Win Rate:            57.63%
║  
║  PROFIT METRICS
║  ───────────────────────────────────────────────────────────
║  Profit Factor:       1.81
║  Average Win:         $367.76
║  Average Loss:        $276.81
║  Largest Win:         $586.53
║  Largest Loss:        $-764.70
║  Average R:R:         1.94
║  
║  RISK METRICS
║  ───────────────────────────────────────────────────────────
║  Max Drawdown:        $2116.83 (13.79%)
║  Sharpe Ratio:        4.42
╚══════════════════════════════════════════════════════════════╝


======================================================================
📋 PERFORMANCE BY RULE
======================================================================

Rule                             Trades   Win Rate   Profit Factor      Net P&L
---------------------------------------------------------------------------
Rule1_618_Golden                     17      47.1%            1.51 $   1,196.33
Rule2_786_DeepDiscount                3      66.7%            3.97 $     710.26
Rule5_ATH_Retest                     19      36.8%            1.12 $     382.14
Rule6_50_Momentum                    20      85.0%            3.59 $   3,294.84
---------------------------------------------------------------------------

📝 Last 10 Trades:
Date                 Rule                         Dir      Entry       Exit          P&L
-------------------------------------------------------------------------------------
2024-11-07 00:00:00  Rule5_ATH_Retest            LONG $ 2,698.90 $ 2,663.45 $    -268.97
2024-11-11 00:00:00  Rule1_618_Golden            LONG $ 2,611.70 $ 2,592.90 $    -266.81
2024-11-27 00:00:00  Rule6_50_Momentum          SHORT $ 2,639.40 $ 2,654.15 $    -263.22
2024-12-18 00:00:00  Rule2_786_DeepDiscount      LONG $ 2,637.00 $ 2,749.42 $     489.20
2025-01-30 00:00:00  Rule5_ATH_Retest            LONG $ 2,823.50 $ 2,908.57 $     505.43
2025-03-07 00:00:00  Rule1_618_Golden           SHORT $ 2,904.20 $ 2,969.43 $    -270.76
2025-03-13 00:00:00  Rule5_ATH_Retest            LONG $ 2,984.80 $ 3,083.77 $     515.95
2025-04-07 00:00:00  Rule6_50_Momentum           LONG $ 2,951.80 $ 3,048.47 $     535.77
2025-04-09 00:00:00  Rule1_618_Golden            LONG $ 3,057.00 $ 3,536.34 $     565.77
2025-10-30 00:00:00  Rule5_ATH_Retest            LONG $ 4,001.80 $ 4,290.08 $     586.53

======================================================================
✅ Backtest Complete!
======================================================================
