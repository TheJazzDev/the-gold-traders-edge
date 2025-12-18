'use client';

import { useEffect, useState } from 'react';
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
import { RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const [timeframe, setTimeframe] = useState('4h');
  const [performanceData, setPerformanceData] = useState<PerformanceSummary | null>(null);
  const [ruleData, setRuleData] = useState<RulePerformance[]>([]);
  const [tradeData, setTradeData] = useState<TradeDetail[]>([]);
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const rules = '1,5,6'; // Optimized profitable rules only

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
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load dashboard data. Make sure the API is running on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeframe]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-amber-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-amber-500 via-yellow-500 to-amber-600 border-b-4 border-amber-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-2">
                <span className="text-4xl">🥇</span>
                The Gold Trader&apos;s Edge
              </h1>
              <p className="text-sm text-amber-100 mt-2">
                Real-time gold trading signals and analytics powered by AI
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="px-4 py-2 bg-white border-2 border-amber-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-300 font-medium text-gray-700"
              >
                <option value="4h">4 Hour</option>
                <option value="1d">Daily</option>
              </select>
              <button
                onClick={fetchData}
                disabled={loading}
                className="px-4 py-2 bg-white text-amber-600 font-semibold rounded-lg hover:bg-amber-50 disabled:opacity-50 flex items-center gap-2 shadow-md transition-all"
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
        {error && (
          <div className="mb-6 bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-500 rounded-lg p-4 shadow-md">
            <div className="flex">
              <div className="shrink-0">
                <svg className="h-6 w-6 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-semibold text-red-900">Error loading data</h3>
                <p className="text-sm text-red-800 mt-1">{error}</p>
                <p className="text-xs text-red-700 mt-2 bg-white/50 px-3 py-2 rounded">
                  Start the API: <code className="font-mono font-semibold">cd packages/engine && ./start_api.sh</code>
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-6">
          {/* Performance Stats */}
          {performanceData && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="text-2xl">📈</span>
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
            <div className="bg-gradient-to-br from-white to-amber-50 rounded-lg border-2 border-amber-200 p-6 shadow-md">
              <h3 className="text-lg font-bold text-amber-900 mb-2 flex items-center gap-2">
                <span>🎯</span> Active Strategy Rules
              </h3>
              <p className="text-sm text-gray-600 mb-4">Only the best-performing rules (backtest-proven):</p>
              <ul className="space-y-3 text-sm">
                <li className="flex items-start gap-3 p-2 bg-gradient-to-r from-amber-50 to-transparent rounded-lg border-l-4 border-amber-500">
                  <span className="text-amber-600 font-bold text-lg">⭐</span>
                  <div>
                    <span className="text-gray-900 font-semibold">50% Momentum</span>
                    <p className="text-xs text-gray-600 mt-0.5">293% return, 76% win rate - Our best performer</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-2 bg-gradient-to-r from-green-50 to-transparent rounded-lg border-l-4 border-green-500">
                  <span className="text-green-600 font-bold">✓</span>
                  <div>
                    <span className="text-gray-900 font-semibold">61.8% Golden Retracement</span>
                    <p className="text-xs text-gray-600 mt-0.5">44% return, 52.6% win rate - Solid and reliable</p>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-2 bg-gradient-to-r from-blue-50 to-transparent rounded-lg border-l-4 border-blue-500">
                  <span className="text-blue-600 font-bold">✓</span>
                  <div>
                    <span className="text-gray-900 font-semibold">ATH Breakout Retest</span>
                    <p className="text-xs text-gray-600 mt-0.5">30% return, 38% win rate - Trend continuation</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="bg-gradient-to-br from-white to-blue-50 rounded-lg border-2 border-blue-200 p-6 shadow-md">
              <h3 className="text-lg font-bold text-blue-900 mb-2 flex items-center gap-2">
                <span>⚙️</span> System Status
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between p-2 bg-white/50 rounded">
                  <span className="text-gray-700 font-medium">API Status:</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm ${
                    error ? 'bg-red-500 text-white' : 'bg-green-500 text-white'
                  }`}>
                    {error ? '🔴 Offline' : '🟢 Online'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2 bg-white/50 rounded">
                  <span className="text-gray-700 font-medium">Timeframe:</span>
                  <span className="font-bold text-blue-600">{timeframe.toUpperCase()}</span>
                </div>
                <div className="flex items-center justify-between p-2 bg-white/50 rounded">
                  <span className="text-gray-700 font-medium">Last Update:</span>
                  <span className="font-bold text-gray-900">{lastUpdate.toLocaleTimeString()}</span>
                </div>
                <div className="flex items-center justify-between p-2 bg-white/50 rounded">
                  <span className="text-gray-700 font-medium">Data Source:</span>
                  <span className="font-bold text-gray-900">Yahoo Finance</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-sm text-gray-500 pt-8 border-t border-gray-200">
            <p>Built with ❤️ using Next.js, FastAPI, and Claude Code</p>
            <p className="mt-1">
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                API Documentation
              </a>
              {' • '}
              <a href="https://github.com/anthropics/claude-code" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                GitHub
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
