# Gold Trading Rules - Comprehensive Testing Results
**Date:** December 20, 2025
**Dataset:** XAUUSD 4H (2023-12-18 to 2025-12-17)
**Initial Balance:** $10,000
**Risk Per Trade:** 2%

---

## 📊 Executive Summary

**Tested 9 Trading Rules:**
- ✅ **6 Profitable** (Profit Factor > 1.0)
- ❌ **3 Unprofitable** (Should be disabled)

**Key Finding:** **Rule 6 (50% Momentum)** is the clear winner, generating **$21,180 profit** with **74% win rate** - more than all other rules combined!

---

## 🏆 PROFITABLE RULES (Ranked by Profit)

### 1. ⭐ Rule 6: 50% Momentum - **SUPERSTAR**
- **Net Profit:** $21,180 (+212%)
- **Win Rate:** 74.0%
- **Profit Factor:** 3.31
- **Sharpe Ratio:** 8.67
- **Total Trades:** 104
- **Status:** ✅ **KEEP & PRIORITIZE**
- **Notes:** By far the best performing rule. This alone could be the entire strategy.

### 2. ✅ Rule 9: London Session Breakout - **STRONG**
- **Net Profit:** $2,621 (+26%)
- **Win Rate:** 58.8%
- **Profit Factor:** 2.74
- **Sharpe Ratio:** 7.90
- **Total Trades:** 17
- **Status:** ✅ **KEEP**
- **Notes:** Excellent performance but limited trade frequency.

### 3. ⚠️  Rule 1: 61.8% Golden Retracement - **MARGINAL**
- **Net Profit:** $2,177 (+22%)
- **Win Rate:** 49.1%
- **Profit Factor:** 1.31
- **Sharpe Ratio:** 2.02
- **Total Trades:** 57
- **Status:** ⚠️ **KEEP (with caution)**
- **Notes:** Marginally profitable. Could be kept for diversification.

### 4. ⚠️  Rule 10: Order Block Retest - **MARGINAL**
- **Net Profit:** $2,110 (+21%)
- **Win Rate:** 38.6%
- **Profit Factor:** 1.14
- **Sharpe Ratio:** 1.00
- **Total Trades:** 132
- **Status:** ⚠️ **KEEP (with caution)**
- **Notes:** Many trades but low win rate. Barely profitable.

### 5. ⚠️  Rule 5: ATH Breakout Retest - **BARELY PROFITABLE**
- **Net Profit:** $287 (+3%)
- **Win Rate:** 38.3%
- **Profit Factor:** 1.06
- **Sharpe Ratio:** 0.41
- **Total Trades:** 115
- **Status:** ⚠️ **CONSIDER DISABLING**
- **Notes:** Barely breaks even. Not worth the risk.

### 6. ⚠️  Rule 12: Bollinger Band Squeeze - **BARELY PROFITABLE**
- **Net Profit:** $87 (+1%)
- **Win Rate:** 31.2%
- **Profit Factor:** 1.07
- **Sharpe Ratio:** 0.47
- **Total Trades:** 16
- **Status:** ⚠️ **CONSIDER DISABLING**
- **Notes:** Almost breakeven. Too close to call.

---

## ❌ UNPROFITABLE RULES (Should be Removed)

### 7. ❌ Rule 7: RSI Divergence - **TERRIBLE**
- **Net Profit:** -$7,689 (-77%)
- **Win Rate:** 30.4%
- **Profit Factor:** 0.67
- **Sharpe Ratio:** -2.83
- **Total Trades:** 286
- **Status:** ❌ **DISABLE IMMEDIATELY**
- **Notes:** Worst performing rule. Loses money consistently.

### 8. ❌ Rule 8: EMA 9/21 Crossover - **BAD**
- **Net Profit:** -$1,330 (-13%)
- **Win Rate:** 34.1%
- **Profit Factor:** 0.91
- **Sharpe Ratio:** -0.69
- **Total Trades:** 91
- **Status:** ❌ **DISABLE**
- **Notes:** Classic lagging indicator. Loses money.

### 9. ❌ Rule 11: VWAP Deviation - **TERRIBLE**
- **Net Profit:** -$1,945 (-19%)
- **Win Rate:** 15.0%
- **Profit Factor:** 0.39
- **Sharpe Ratio:** -7.01
- **Total Trades:** 20
- **Status:** ❌ **DISABLE IMMEDIATELY**
- **Notes:** Only 15% win rate. Mean reversion doesn't work on gold trends.

---

## 🎯 RECOMMENDATIONS FOR PRODUCTION

### Tier 1: Production Ready
**Use ONLY Rule 6 (50% Momentum)**
- This single rule outperforms everything else
- 74% win rate with 3.31 profit factor is institutional-grade
- 8.67 Sharpe ratio is exceptional
- **Recommendation:** Build production signal service around Rule 6 ONLY

### Tier 2: Optional Add-Ons (if you want diversification)
**Add Rule 9 (London Breakout)**
- Strong metrics (58.8% win rate, 2.74 PF)
- Low correlation with Rule 6 (time-based vs. pattern-based)
- Could catch different market conditions

### Tier 3: Not Recommended
- Rules 1, 5, 10, 12: Marginal/barely profitable
- Rules 7, 8, 11: Unprofitable - disable immediately

---

## 💡 PRODUCTION STRATEGY

### Conservative Approach (Recommended)
```python
strategy.rules_enabled = {
    'momentum_50': True,              # Rule 6 - The moneymaker
    'golden_retracement': False,      # Marginal
    'ath_breakout_retest': False,     # Barely profitable
    'rsi_divergence': False,          # LOSING MONEY
    'ema_crossover': False,           # LOSING MONEY
    'london_breakout': False,         # Good but optional
    'order_block': False,             # Marginal
    'vwap_deviation': False,          # LOSING MONEY
    'bollinger_squeeze': False,       # Barely profitable
}
```

### Aggressive Approach (More signals, more risk)
```python
strategy.rules_enabled = {
    'momentum_50': True,              # Rule 6 - Primary
    'london_breakout': True,          # Rule 9 - Secondary
    'golden_retracement': False,      # Optional
    'ath_breakout_retest': False,
    'rsi_divergence': False,          # Disable
    'ema_crossover': False,           # Disable
    'order_block': False,
    'vwap_deviation': False,          # Disable
    'bollinger_squeeze': False,
}
```

---

## 📈 NEXT STEPS

1. ✅ **Update default strategy** to disable unprofitable rules (7, 8, 11)
2. ✅ **Set Rule 6 as primary** signal generator
3. ⚠️  **Walk-forward analysis** on Rule 6 to validate robustness
4. ⚠️  **Paper trade Rule 6** for 30 days before going live
5. ⚠️  **Monitor live performance** vs. backtest
6. ✅ **Build production API** around Rule 6 signals

---

## ⚠️  CRITICAL WARNING

**Rule 6 has 74% win rate - this is SUSPICIOUSLY HIGH**

Before going to production:
- ✅ Check for look-ahead bias in the code
- ✅ Verify the logic doesn't use future data
- ✅ Test on out-of-sample data (2026 data when available)
- ✅ Run walk-forward analysis (train/test splits)
- ✅ Paper trade for 30-60 days minimum

**DO NOT risk real money until Rule 6 is validated in live conditions.**

---

*Generated by test_all_rules.py on 2025-12-20*
