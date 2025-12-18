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
import { Calendar, TrendingUp, Play, BarChart3, History, Settings } from 'lucide-react';

export default function DashboardPage() {
  const [timeframe, setTimeframe] = useState('4h');
  const [performanceData, setPerformanceData] = useState<PerformanceSummary | null>(null);
  const [ruleData, setRuleData] = useState<RulePerformance[]>([]);
  const [tradeData, setTradeData] = useState<TradeDetail[]>([]);
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [activeNav, setActiveNav] = useState('dashboard');

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

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'trades', label: 'Trade History', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <span className="text-2xl">🥇</span>
              <span className="text-xl font-bold text-gray-900">Gold Trader&apos;s Edge</span>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveNav(item.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeNav === item.id
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </button>
                );
              })}
            </nav>

            {/* Right side - Status */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-600">
                <span className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'}`}></span>
                <span>{error ? 'API Offline' : 'API Online'}</span>
              </div>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                API Docs
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Backtest Controls */}
        <div className="mb-8 bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-end gap-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <Calendar className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Backtest Configuration</h2>
                <p className="text-sm text-gray-500">Select timeframe and date range</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 flex-1">
              {/* Timeframe selector */}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">Timeframe</label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 text-gray-700"
                >
                  <option value="4h">4 Hour</option>
                  <option value="1d">Daily</option>
                </select>
              </div>

              {/* Date filter toggle */}
              <label className="flex items-center gap-2 text-gray-700 cursor-pointer mt-5">
                <input
                  type="checkbox"
                  checked={useDateRange}
                  onChange={(e) => setUseDateRange(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-gray-900 focus:ring-gray-400"
                />
                <span className="text-sm font-medium">Use date filter</span>
              </label>

              {/* Date range inputs */}
              <div className="flex items-center gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500 font-medium">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    disabled={!useDateRange}
                    className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 disabled:opacity-50 disabled:cursor-not-allowed font-mono text-sm"
                  />
                </div>
                <span className="text-gray-400 mt-5">to</span>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500 font-medium">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    disabled={!useDateRange}
                    className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 disabled:opacity-50 disabled:cursor-not-allowed font-mono text-sm"
                  />
                </div>
              </div>

              {/* Run Backtest button */}
              <button
                onClick={handleRunBacktest}
                disabled={loading}
                className="px-6 py-2 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 flex items-center gap-2 transition-colors mt-5"
              >
                <Play className={`h-4 w-4 ${loading ? 'animate-pulse' : ''}`} />
                {loading ? 'Running...' : 'Run Backtest'}
              </button>
            </div>
          </div>

          {performanceData?.start_date && performanceData?.end_date && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-sm text-gray-500">
                <span className="font-medium text-gray-700">Current period:</span>{' '}
                {performanceData.start_date} to {performanceData.end_date}
                <span className="ml-4 text-gray-400">Last updated: {lastUpdate.toLocaleTimeString()}</span>
              </p>
            </div>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="shrink-0">
                <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error loading data</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
                <p className="text-xs text-red-600 mt-2 bg-red-100 px-2 py-1 rounded font-mono inline-block">
                  cd packages/engine && ./start_api.sh
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-8">
          {/* Performance Stats */}
          {performanceData && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-gray-600" />
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
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Active Trading Rules</h3>
              <p className="text-sm text-gray-500 mb-4">Only backtested, profitable rules:</p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border-l-4 border-green-500">
                  <span className="text-green-600 font-bold">1</span>
                  <div>
                    <span className="text-gray-900 font-medium">50% Momentum</span>
                    <p className="text-xs text-gray-500 mt-0.5">85% win rate, 5.26 profit factor</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border-l-4 border-gray-400">
                  <span className="text-gray-600 font-bold">2</span>
                  <div>
                    <span className="text-gray-900 font-medium">61.8% Golden Retracement</span>
                    <p className="text-xs text-gray-500 mt-0.5">56% win rate, 1.37 profit factor</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border-l-4 border-gray-400">
                  <span className="text-gray-600 font-bold">3</span>
                  <div>
                    <span className="text-gray-900 font-medium">ATH Breakout Retest</span>
                    <p className="text-xs text-gray-500 mt-0.5">43% win rate, 1.50 profit factor</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">API Status</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    error ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {error ? 'Offline' : 'Online'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">Timeframe</span>
                  <span className="font-medium text-gray-900">{timeframe.toUpperCase()}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">Last Update</span>
                  <span className="font-medium text-gray-900">{lastUpdate.toLocaleTimeString()}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-gray-600">Data Source</span>
                  <span className="font-medium text-gray-900">Yahoo Finance</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-sm text-gray-500 pt-8 border-t border-gray-200">
            <p>Built with Next.js, FastAPI, and Claude Code</p>
          </div>
        </div>
      </main>
    </div>
  );
}
