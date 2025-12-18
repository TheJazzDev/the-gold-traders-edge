'use client';

import { useEffect, useState, useCallback } from 'react';
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
  type DateRange,
} from '@/lib/api';
import { RefreshCw, Calendar, TrendingUp, Play } from 'lucide-react';

export default function DashboardPage() {
  const [timeframe, setTimeframe] = useState('4h');
  const [performanceData, setPerformanceData] = useState<PerformanceSummary | null>(null);
  const [ruleData, setRuleData] = useState<RulePerformance[]>([]);
  const [tradeData, setTradeData] = useState<TradeDetail[]>([]);
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Date range state
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [useDateRange, setUseDateRange] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const rules = '1,5,6'; // Only profitable rules
      const dateRange: DateRange | undefined = useDateRange
        ? { startDate, endDate }
        : undefined;

      const [performance, rules_data, trades, ohlcv] = await Promise.all([
        getPerformanceSummary(timeframe, rules, dateRange),
        getRulePerformance(timeframe, rules, dateRange),
        getTradeHistory(timeframe, rules, dateRange),
        getOHLCV(timeframe, 500),
      ]);

      setPerformanceData(performance);
      setRuleData(rules_data);
      setTradeData(trades);
      setCandleData(ohlcv.candles);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load dashboard data. Make sure the API is running on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  }, [timeframe, startDate, endDate, useDateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRunBacktest = () => {
    fetchData();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-500 border-b-4 border-amber-700 shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
                <span className="text-4xl drop-shadow-lg">🥇</span>
                <span className="drop-shadow-md">The Gold Trader&apos;s Edge</span>
              </h1>
              <p className="text-sm text-amber-100 mt-2 font-medium">
                Professional XAUUSD Trading Signals & Analytics
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="px-4 py-2.5 bg-white border-2 border-amber-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-300 font-semibold text-gray-700 shadow-md"
              >
                <option value="4h">4 Hour</option>
                <option value="1d">Daily</option>
              </select>
              <button
                onClick={fetchData}
                disabled={loading}
                className="px-4 py-2.5 bg-white text-amber-600 font-semibold rounded-lg hover:bg-amber-50 disabled:opacity-50 flex items-center gap-2 shadow-md transition-all hover:shadow-lg"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Date Range Selector Card */}
        <div className="mb-8 bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl border border-slate-600 p-6 shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-end gap-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-500/20 rounded-xl">
                <Calendar className="h-6 w-6 text-amber-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Backtest Date Range</h2>
                <p className="text-sm text-slate-400">Select a period to analyze strategy performance</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 flex-1">
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useDateRange}
                  onChange={(e) => setUseDateRange(e.target.checked)}
                  className="w-5 h-5 rounded border-slate-500 text-amber-500 focus:ring-amber-500 bg-slate-700"
                />
                <span className="font-medium">Use date filter</span>
              </label>

              <div className="flex items-center gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-400 font-medium">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    disabled={!useDateRange}
                    className="px-4 py-2.5 bg-slate-700 border border-slate-500 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed font-mono"
                  />
                </div>
                <span className="text-slate-400 mt-5">to</span>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-400 font-medium">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    disabled={!useDateRange}
                    className="px-4 py-2.5 bg-slate-700 border border-slate-500 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed font-mono"
                  />
                </div>
              </div>

              <button
                onClick={handleRunBacktest}
                disabled={loading}
                className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-yellow-500 text-white font-bold rounded-lg hover:from-amber-600 hover:to-yellow-600 disabled:opacity-50 flex items-center gap-2 shadow-lg transition-all hover:shadow-xl mt-5"
              >
                <Play className="h-4 w-4" />
                Run Backtest
              </button>
            </div>
          </div>

          {performanceData?.start_date && performanceData?.end_date && (
            <div className="mt-4 pt-4 border-t border-slate-600">
              <p className="text-sm text-slate-400">
                <span className="font-medium text-slate-300">Current period:</span>{' '}
                {performanceData.start_date} to {performanceData.end_date}
              </p>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-6 bg-gradient-to-r from-red-900/50 to-red-800/50 border border-red-500/50 rounded-xl p-5 shadow-lg">
            <div className="flex">
              <div className="shrink-0">
                <svg className="h-6 w-6 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-4">
                <h3 className="text-sm font-bold text-red-300">Error loading data</h3>
                <p className="text-sm text-red-200 mt-1">{error}</p>
                <p className="text-xs text-red-300/80 mt-2 bg-red-950/50 px-3 py-2 rounded font-mono">
                  Start the API: cd packages/engine && ./start_api.sh
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-8">
          {/* Performance Stats */}
          {performanceData && (
            <div>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-3">
                <TrendingUp className="h-6 w-6 text-amber-400" />
                Performance Overview
              </h2>
              <PerformanceStats data={performanceData} loading={loading} />
            </div>
          )}

          {/* Rule Performance Chart */}
          {ruleData.length > 0 && (
            <div>
              <RulePerformanceChart data={ruleData} loading={loading} />
            </div>
          )}

          {/* Price Chart with Signals */}
          {candleData.length > 0 && tradeData.length > 0 && (
            <div>
              <PriceChart candles={candleData} trades={tradeData} loading={loading} />
            </div>
          )}

          {/* Trade History Table */}
          {tradeData.length > 0 && (
            <div>
              <TradeHistoryTable data={tradeData} loading={loading} />
            </div>
          )}

          {/* Info Cards */}
          <div className="grid md:grid-cols-2 gap-6 mt-8">
            <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-xl border border-slate-600 p-6 shadow-lg">
              <h3 className="text-lg font-bold text-amber-400 mb-3 flex items-center gap-2">
                <span className="text-2xl">🎯</span> Active Trading Rules
              </h3>
              <p className="text-sm text-slate-400 mb-4">Only backtested, profitable rules:</p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-3 p-3 bg-gradient-to-r from-amber-500/10 to-transparent rounded-lg border-l-4 border-amber-500">
                  <span className="text-amber-400 font-bold text-lg">⭐</span>
                  <div>
                    <span className="text-white font-semibold">50% Momentum</span>
                    <p className="text-xs text-slate-400 mt-0.5">85% win rate, 5.26 profit factor - Best performer</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-gradient-to-r from-green-500/10 to-transparent rounded-lg border-l-4 border-green-500">
                  <span className="text-green-400 font-bold">✓</span>
                  <div>
                    <span className="text-white font-semibold">61.8% Golden Retracement</span>
                    <p className="text-xs text-slate-400 mt-0.5">56% win rate, 1.37 profit factor</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-gradient-to-r from-blue-500/10 to-transparent rounded-lg border-l-4 border-blue-500">
                  <span className="text-blue-400 font-bold">✓</span>
                  <div>
                    <span className="text-white font-semibold">ATH Breakout Retest</span>
                    <p className="text-xs text-slate-400 mt-0.5">43% win rate, 1.50 profit factor</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-xl border border-slate-600 p-6 shadow-lg">
              <h3 className="text-lg font-bold text-blue-400 mb-3 flex items-center gap-2">
                <span className="text-2xl">⚙️</span> System Status
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                  <span className="text-slate-300 font-medium">API Status:</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm ${
                    error ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'
                  }`}>
                    {error ? '● Offline' : '● Online'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                  <span className="text-slate-300 font-medium">Timeframe:</span>
                  <span className="font-bold text-amber-400">{timeframe.toUpperCase()}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                  <span className="text-slate-300 font-medium">Last Update:</span>
                  <span className="font-bold text-white">{lastUpdate.toLocaleTimeString()}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                  <span className="text-slate-300 font-medium">Data Source:</span>
                  <span className="font-bold text-white">Yahoo Finance</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-sm text-slate-500 pt-8 border-t border-slate-700">
            <p>Built with Next.js, FastAPI, and Claude Code</p>
            <p className="mt-2 space-x-4">
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="text-amber-400 hover:text-amber-300 hover:underline transition-colors">
                API Documentation
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
