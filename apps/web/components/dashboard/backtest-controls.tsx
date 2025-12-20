'use client';

import { useState } from 'react';
import { RefreshCw, Play } from 'lucide-react';
import { TimeframeSelector } from './timeframe-selector';
import { RuleSelector } from './rule-selector';
import { ErrorDisplay } from './error-display';
import { WelcomeState } from './welcome-state';
import { InfoCards } from './info-cards';
import { PerformanceStats } from './performance-stats';
import { RulePerformanceChart } from './rule-performance-chart';
import { TradeHistoryTable } from './trade-history-table';
import { PriceChart } from './price-chart';
import {
  runBacktest,
  getOHLCV,
  type PerformanceSummary,
  type RulePerformance,
  type TradeDetail,
  type Candle,
} from '@/lib/api';
import { ALL_RULES, PROFITABLE_RULES } from '@/lib/constants';

export function BacktestControls() {
  const [timeframe, setTimeframe] = useState('4h');
  const [selectedRules, setSelectedRules] = useState<string[]>([
    ...PROFITABLE_RULES,
  ]);
  const [performanceData, setPerformanceData] =
    useState<PerformanceSummary | null>(null);
  const [ruleData, setRuleData] = useState<RulePerformance[]>([]);
  const [tradeData, setTradeData] = useState<TradeDetail[]>([]);
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [hasRun, setHasRun] = useState(false);

  const handleRuleToggle = (ruleId: string) => {
    setSelectedRules((prev) =>
      prev.includes(ruleId)
        ? prev.filter((id) => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  const selectAllRules = () => {
    setSelectedRules(ALL_RULES.map((r) => r.id));
  };

  const selectProfitableRules = () => {
    setSelectedRules([...PROFITABLE_RULES]);
  };

  const clearAllRules = () => {
    setSelectedRules([]);
  };

  const handleRunBacktest = async () => {
    if (selectedRules.length === 0) {
      setError('Please select at least one rule to run the backtest.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const rules = selectedRules.join(',');

      // Run backtest once and get OHLCV data in parallel
      const [backtestResult, ohlcv] = await Promise.all([
        runBacktest(timeframe, rules),
        getOHLCV(timeframe, 500),
      ]);

      setPerformanceData(backtestResult.summary);
      setRuleData(backtestResult.rules);
      setTradeData(backtestResult.trades);
      setCandleData(ohlcv.candles);
      setLastUpdate(new Date());
      setHasRun(true);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(
        'Failed to load dashboard data. Make sure the API is running on http://localhost:8000'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Control Panel */}
      <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-4 sm:p-6 mb-8 shadow-2xl'>
        <h2 className='text-lg sm:text-xl font-bold text-white mb-4 sm:mb-6 flex items-center gap-2'>
          <span className='text-xl sm:text-2xl'>⚙️</span>
          Backtest Configuration
        </h2>

        <div className='grid lg:grid-cols-3 gap-4 sm:gap-6'>
          {/* Timeframe Selection */}
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />

          {/* Rule Selection */}
          <RuleSelector
            selectedRules={selectedRules}
            onRuleToggle={handleRuleToggle}
            onSelectAll={selectAllRules}
            onSelectProfitable={selectProfitableRules}
            onClearAll={clearAllRules}
          />
        </div>

        {/* Run Button */}
        <div className='mt-4 sm:mt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0'>
          <div className='text-xs sm:text-sm text-white/60'>
            {lastUpdate ? (
              <span>Last run: {lastUpdate.toLocaleString()}</span>
            ) : (
              <span>Configure settings and click Run to start backtest</span>
            )}
          </div>
          <button
            onClick={handleRunBacktest}
            disabled={loading || selectedRules.length === 0}
            className='group relative px-6 sm:px-8 py-3 sm:py-4 bg-linear-to-r from-amber-500 via-yellow-500 to-amber-500 text-slate-900 font-bold text-base sm:text-lg rounded-xl hover:shadow-2xl hover:shadow-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:scale-105 active:scale-95 w-full sm:w-auto'>
            <span className='flex items-center justify-center gap-2 sm:gap-3'>
              {loading ? (
                <RefreshCw className='w-4 h-4 sm:w-5 sm:h-5 animate-spin' />
              ) : (
                <Play className='w-4 h-4 sm:w-5 sm:h-5' />
              )}
              {loading ? 'Running Backtest...' : 'Run Backtest'}
            </span>
            <div className='absolute inset-0 rounded-xl bg-linear-to-r from-white/0 via-white/25 to-white/0 opacity-0 group-hover:opacity-100 transition-opacity'></div>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && <ErrorDisplay error={error} />}

      {/* Results */}
      {hasRun && !error && (
        <div className='space-y-6 sm:space-y-8'>
          {/* Performance Stats */}
          {performanceData && (
            <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-4 sm:p-6 shadow-2xl'>
              <h2 className='text-lg sm:text-xl font-bold text-white mb-4 sm:mb-6 flex items-center gap-2'>
                <span className='text-xl sm:text-2xl'>📈</span>
                Performance Overview
              </h2>
              <PerformanceStats data={performanceData} loading={loading} />
            </div>
          )}

          {/* Rule Performance Chart */}
          {ruleData.length > 0 && (
            <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-4 sm:p-6 shadow-2xl'>
              <RulePerformanceChart data={ruleData} loading={loading} />
            </div>
          )}

          {/* Price Chart with Signals */}
          {candleData.length > 0 && tradeData.length > 0 && (
            <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-4 sm:p-6 shadow-2xl'>
              <PriceChart
                candles={candleData}
                trades={tradeData}
                loading={loading}
              />
            </div>
          )}

          {/* Trade History Table */}
          {tradeData.length > 0 && (
            <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-4 sm:p-6 shadow-2xl'>
              <TradeHistoryTable data={tradeData} loading={loading} />
            </div>
          )}
        </div>
      )}

      {/* Welcome State - Before First Run */}
      {!hasRun && !error && <WelcomeState />}

      {/* Info Cards */}
      <InfoCards
        selectedRules={selectedRules}
        timeframe={timeframe}
        lastUpdate={lastUpdate}
        error={error}
        rulePerformance={ruleData}
      />
    </>
  );
}
