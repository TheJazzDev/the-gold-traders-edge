'use client';

import { useState } from 'react';
import { PerformanceStats } from '@/components/dashboard/performance-stats';
import { RulePerformanceChart } from '@/components/dashboard/rule-performance-chart';
import { TradeHistoryTable } from '@/components/dashboard/trade-history-table';
import { PriceChart } from '@/components/dashboard/price-chart';
import {
  getPerformanceSummary,
  getRulePerformance,
  getTradeHistory,
  getOHLCV,
  type PerformanceSummary,
  type RulePerformance,
  type TradeDetail,
  type Candle,
} from '@/lib/api';
import { RefreshCw, Play, ChevronDown } from 'lucide-react';

// All 6 trading rules with their details
const ALL_RULES = [
  { id: '1', name: '61.8% Golden Retracement', description: 'Price retraces to golden ratio level', performance: '44% return, 52.6% win rate' },
  { id: '2', name: '78.6% Deep Discount', description: 'Deep pullback entry in strong trends', performance: '-33% return (disabled by default)' },
  { id: '3', name: '23.6% Shallow Pullback', description: 'Quick continuation in momentum', performance: '-6% return (disabled by default)' },
  { id: '4', name: 'Consolidation Breakout', description: 'Range breakout after sideways action', performance: '0% return (disabled by default)' },
  { id: '5', name: 'ATH Breakout Retest', description: 'Retest of all-time high as support', performance: '30% return, 38% win rate' },
  { id: '6', name: '50% Momentum', description: 'Equilibrium entry in strong momentum', performance: '293% return, 76% win rate ⭐' },
];

// All available timeframes
const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
];

export default function DashboardPage() {
  const [timeframe, setTimeframe] = useState('4h');
  const [selectedRules, setSelectedRules] = useState<string[]>(['1', '5', '6']); // Default profitable rules
  const [performanceData, setPerformanceData] = useState<PerformanceSummary | null>(null);
  const [ruleData, setRuleData] = useState<RulePerformance[]>([]);
  const [tradeData, setTradeData] = useState<TradeDetail[]>([]);
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [hasRun, setHasRun] = useState(false);

  const handleRuleToggle = (ruleId: string) => {
    setSelectedRules(prev =>
      prev.includes(ruleId)
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  const selectAllRules = () => {
    setSelectedRules(ALL_RULES.map(r => r.id));
  };

  const selectProfitableRules = () => {
    setSelectedRules(['1', '5', '6']);
  };

  const clearAllRules = () => {
    setSelectedRules([]);
  };

  const runBacktest = async () => {
    if (selectedRules.length === 0) {
      setError('Please select at least one rule to run the backtest.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const rules = selectedRules.join(',');

      const [performance, rules_data, trades, ohlcv] = await Promise.all([
        getPerformanceSummary(timeframe, rules),
        getRulePerformance(timeframe, rules),
        getTradeHistory(timeframe, rules),
        getOHLCV(timeframe, 500),
      ]);

      setPerformanceData(performance);
      setRuleData(rules_data);
      setTradeData(trades);
      setCandleData(ohlcv.candles);
      setLastUpdate(new Date());
      setHasRun(true);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load dashboard data. Make sure the API is running on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-amber-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Header */}
      <header className="relative bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-500 shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=\"30\" height=\"30\" viewBox=\"0 0 30 30\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cpath d=\"M1.22676 0C1.91374 0 2.45351 0.539773 2.45351 1.22676C2.45351 1.91374 1.91374 2.45351 1.22676 2.45351C0.539773 2.45351 0 1.91374 0 1.22676C0 0.539773 0.539773 0 1.22676 0Z\" fill=\"rgba(255,255,255,0.07)\"%3E%3C/path%3E%3C/svg%3E')] opacity-50"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
            <div>
              <h1 className="text-4xl md:text-5xl font-black text-white flex items-center gap-3 drop-shadow-lg">
                <span className="text-5xl animate-bounce">🥇</span>
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-yellow-100 to-white">
                  The Gold Trader&apos;s Edge
                </span>
              </h1>
              <p className="text-amber-100 mt-3 text-lg font-medium">
                Professional XAUUSD backtesting & signal analytics
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Control Panel */}
        <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 mb-8 shadow-2xl">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <span className="text-2xl">⚙️</span>
            Backtest Configuration
          </h2>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Timeframe Selection */}
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-amber-300">
                Timeframe
              </label>
              <div className="relative">
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full px-4 py-3 bg-white/10 border-2 border-amber-400/50 rounded-xl text-white font-medium focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent appearance-none cursor-pointer hover:bg-white/20 transition-all"
                >
                  {TIMEFRAMES.map(tf => (
                    <option key={tf.value} value={tf.value} className="bg-slate-800 text-white">
                      {tf.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-400 pointer-events-none" />
              </div>
            </div>

            {/* Rule Selection */}
            <div className="lg:col-span-2 space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-semibold text-amber-300">
                  Trading Rules ({selectedRules.length} selected)
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={selectProfitableRules}
                    className="text-xs px-3 py-1 bg-green-500/20 text-green-300 rounded-full hover:bg-green-500/30 transition-all border border-green-500/30"
                  >
                    Profitable Only
                  </button>
                  <button
                    onClick={selectAllRules}
                    className="text-xs px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full hover:bg-blue-500/30 transition-all border border-blue-500/30"
                  >
                    Select All
                  </button>
                  <button
                    onClick={clearAllRules}
                    className="text-xs px-3 py-1 bg-red-500/20 text-red-300 rounded-full hover:bg-red-500/30 transition-all border border-red-500/30"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {ALL_RULES.map((rule) => {
                  const isSelected = selectedRules.includes(rule.id);
                  const isProfitable = ['1', '5', '6'].includes(rule.id);

                  return (
                    <label
                      key={rule.id}
                      className={`relative flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-gradient-to-br from-amber-500/30 to-yellow-500/20 border-2 border-amber-400 shadow-lg shadow-amber-500/20'
                          : 'bg-white/5 border-2 border-white/10 hover:border-white/30 hover:bg-white/10'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleRuleToggle(rule.id)}
                        className="sr-only"
                      />
                      <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
                        isSelected
                          ? 'bg-amber-500 border-amber-500'
                          : 'border-white/40 bg-transparent'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-semibold ${isSelected ? 'text-amber-300' : 'text-white/80'}`}>
                            Rule {rule.id}
                          </span>
                          {isProfitable && (
                            <span className="text-xs px-1.5 py-0.5 bg-green-500/30 text-green-300 rounded-full">
                              ✓ Profitable
                            </span>
                          )}
                          {rule.id === '6' && (
                            <span className="text-xs">⭐</span>
                          )}
                        </div>
                        <p className="text-xs text-white/60 truncate mt-0.5">
                          {rule.name}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Run Button */}
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-white/60">
              {lastUpdate ? (
                <span>Last run: {lastUpdate.toLocaleString()}</span>
              ) : (
                <span>Configure settings and click Run to start backtest</span>
              )}
            </div>
            <button
              onClick={runBacktest}
              disabled={loading || selectedRules.length === 0}
              className="group relative px-8 py-4 bg-gradient-to-r from-amber-500 via-yellow-500 to-amber-500 text-slate-900 font-bold text-lg rounded-xl hover:shadow-2xl hover:shadow-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:scale-105 active:scale-95"
            >
              <span className="flex items-center gap-3">
                {loading ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
                {loading ? 'Running Backtest...' : 'Run Backtest'}
              </span>
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-white/0 via-white/25 to-white/0 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-gradient-to-r from-red-500/20 to-red-600/20 backdrop-blur-xl border-2 border-red-500/50 rounded-2xl p-6 shadow-xl">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-red-500/30 rounded-full">
                <svg className="h-6 w-6 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-red-300">Error</h3>
                <p className="text-red-200 mt-1">{error}</p>
                <p className="text-sm text-red-300/80 mt-3 bg-black/20 px-4 py-2 rounded-lg inline-block">
                  Start the API: <code className="font-mono font-bold">cd packages/engine && ./start_api.sh</code>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {hasRun && !error && (
          <div className="space-y-8">
            {/* Performance Stats */}
            {performanceData && (
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl">
                <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                  <span className="text-2xl">📈</span>
                  Performance Overview
                </h2>
                <PerformanceStats data={performanceData} loading={loading} />
              </div>
            )}

            {/* Rule Performance Chart */}
            {ruleData.length > 0 && (
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl">
                <RulePerformanceChart data={ruleData} loading={loading} />
              </div>
            )}

            {/* Price Chart with Signals */}
            {candleData.length > 0 && tradeData.length > 0 && (
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl">
                <PriceChart candles={candleData} trades={tradeData} loading={loading} />
              </div>
            )}

            {/* Trade History Table */}
            {tradeData.length > 0 && (
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl">
                <TradeHistoryTable data={tradeData} loading={loading} />
              </div>
            )}
          </div>
        )}

        {/* Welcome State - Before First Run */}
        {!hasRun && !error && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-amber-500 to-yellow-500 rounded-full mb-6 shadow-2xl shadow-amber-500/30">
              <span className="text-5xl">📊</span>
            </div>
            <h2 className="text-3xl font-bold text-white mb-4">Ready to Backtest</h2>
            <p className="text-white/60 text-lg max-w-md mx-auto mb-8">
              Select your preferred timeframe and trading rules above, then click the Run button to start the backtest.
            </p>
            <div className="inline-flex items-center gap-2 text-amber-400 text-sm">
              <svg className="w-5 h-5 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              Configure settings above and click Run Backtest
            </div>
          </div>
        )}

        {/* Info Cards */}
        <div className="grid md:grid-cols-2 gap-6 mt-8">
          <div className="bg-gradient-to-br from-amber-500/20 to-yellow-500/10 backdrop-blur-xl rounded-2xl border border-amber-500/30 p-6 shadow-xl">
            <h3 className="text-lg font-bold text-amber-300 mb-4 flex items-center gap-2">
              <span>🎯</span> Trading Rules Guide
            </h3>
            <ul className="space-y-3 text-sm">
              {ALL_RULES.map(rule => (
                <li key={rule.id} className={`flex items-start gap-3 p-2 rounded-lg transition-all ${
                  selectedRules.includes(rule.id)
                    ? 'bg-amber-500/20 border-l-4 border-amber-400'
                    : 'bg-white/5'
                }`}>
                  <span className={`font-bold ${selectedRules.includes(rule.id) ? 'text-amber-400' : 'text-white/40'}`}>
                    #{rule.id}
                  </span>
                  <div>
                    <span className={selectedRules.includes(rule.id) ? 'text-white font-medium' : 'text-white/60'}>
                      {rule.name}
                    </span>
                    <p className="text-xs text-white/40 mt-0.5">{rule.performance}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/10 backdrop-blur-xl rounded-2xl border border-blue-500/30 p-6 shadow-xl">
            <h3 className="text-lg font-bold text-blue-300 mb-4 flex items-center gap-2">
              <span>⚙️</span> System Status
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                <span className="text-white/70 font-medium">API Status</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  error ? 'bg-red-500 text-white' : 'bg-green-500 text-white'
                }`}>
                  {error ? '🔴 Offline' : '🟢 Online'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                <span className="text-white/70 font-medium">Selected Timeframe</span>
                <span className="font-bold text-blue-300">{TIMEFRAMES.find(t => t.value === timeframe)?.label}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                <span className="text-white/70 font-medium">Active Rules</span>
                <span className="font-bold text-amber-300">{selectedRules.length} of 6</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                <span className="text-white/70 font-medium">Last Update</span>
                <span className="font-bold text-white">{lastUpdate?.toLocaleTimeString() || 'Never'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-white/40 pt-12 mt-8 border-t border-white/10">
          <p className="text-white/60">Built with ❤️ using Next.js, FastAPI, and Claude Code</p>
          <p className="mt-2">
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="text-amber-400 hover:text-amber-300 transition-colors">
              API Documentation
            </a>
            {' • '}
            <a href="https://github.com/anthropics/claude-code" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 transition-colors">
              GitHub
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
