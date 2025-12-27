'use client';

import { useSignals } from '@/lib/hooks/useSignals';
import { useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MarketStatus, MarketStatusBadge } from '@/components/market/MarketStatus';
import {
  TrendingUp,
  TrendingDown,
  Home,
  Filter,
  RefreshCw,
  Clock,
  Target,
  Shield,
  ArrowUpRight,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function SignalsPage() {
  const [timeframeFilter, setTimeframeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading, refetch } = useSignals({
    limit: 50,
    timeframe: timeframeFilter === 'all' ? undefined : timeframeFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
  });

  const signals = data?.signals || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 -left-48 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 -right-48 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <nav className="relative border-b border-white/10 bg-slate-950/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" className="text-white hover:bg-white/10">
                  <Home className="w-4 h-4 mr-2" />
                  Home
                </Button>
              </Link>
              <div className="hidden sm:flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm text-gray-400">Live Signals</span>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="hidden md:block">
                <MarketStatusBadge />
              </div>
              <Link href="/user">
                <Button variant="outline" className="border-white/20 text-white hover:bg-white/10 text-sm sm:text-base px-3 sm:px-4">
                  Dashboard
                </Button>
              </Link>
              <Button
                onClick={() => refetch()}
                size="icon"
                variant="ghost"
                className="text-white hover:bg-white/10 w-8 h-8 sm:w-10 sm:h-10"
              >
                <RefreshCw className="w-3 h-3 sm:w-4 sm:h-4" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Page Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-2 sm:mb-3">
            Live Trading Signals
          </h1>
          <p className="text-sm sm:text-base text-gray-400">
            Real-time XAUUSD signals across multiple timeframes
          </p>
        </div>

        {/* Market Status */}
        <div className="mb-6 sm:mb-8">
          <MarketStatus />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">Timeframe:</span>
          </div>
          {['all', '5m', '15m', '30m', '1h', '4h', '1d'].map((tf) => (
            <Button
              key={tf}
              size="sm"
              variant={timeframeFilter === tf ? 'default' : 'outline'}
              className={
                timeframeFilter === tf
                  ? 'bg-amber-500 hover:bg-amber-600'
                  : 'border-white/20 text-white hover:bg-white/10'
              }
              onClick={() => setTimeframeFilter(tf)}
            >
              {tf === 'all' ? 'All' : tf.toUpperCase()}
            </Button>
          ))}

          <div className="w-px h-8 bg-white/10" />

          {['all', 'PENDING', 'ACTIVE', 'CLOSED'].map((status) => (
            <Button
              key={status}
              size="sm"
              variant={statusFilter === status ? 'default' : 'outline'}
              className={
                statusFilter === status
                  ? 'bg-amber-500 hover:bg-amber-600'
                  : 'border-white/20 text-white hover:bg-white/10'
              }
              onClick={() => setStatusFilter(status)}
            >
              {status === 'all' ? 'All Status' : status}
            </Button>
          ))}
        </div>

        {/* Signals Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Card
                key={i}
                className="p-6 bg-white/5 border-white/10 backdrop-blur-xl animate-pulse"
              >
                <div className="h-32" />
              </Card>
            ))}
          </div>
        ) : signals.length === 0 ? (
          <Card className="p-12 bg-white/5 border-white/10 backdrop-blur-xl text-center">
            <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No signals found matching your filters</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {signals.map((signal) => {
              const isLong = signal.direction === 'LONG';
              const profit = signal.entry_price * (signal.risk_reward_ratio / 100);

              return (
                <Card
                  key={signal.id}
                  className="p-6 bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all group"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          isLong
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {isLong ? (
                          <TrendingUp className="w-6 h-6" />
                        ) : (
                          <TrendingDown className="w-6 h-6" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Badge
                            variant={isLong ? 'default' : 'destructive'}
                            className="font-semibold"
                          >
                            {signal.direction}
                          </Badge>
                          <Badge variant="outline" className="border-white/20 text-white">
                            {signal.timeframe.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-400">{signal.strategy_name}</p>
                      </div>
                    </div>

                    <Badge
                      variant={
                        signal.status === 'ACTIVE'
                          ? 'default'
                          : signal.status === 'CLOSED'
                          ? 'secondary'
                          : 'outline'
                      }
                      className={
                        signal.status === 'ACTIVE'
                          ? 'bg-green-500/20 text-green-400 border-green-500/40'
                          : ''
                      }
                    >
                      {signal.status}
                    </Badge>
                  </div>

                  {/* Price Levels */}
                  <div className="grid grid-cols-3 gap-4 mb-4 p-4 rounded-lg bg-black/20">
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <Target className="w-3 h-3 text-blue-400" />
                        <span className="text-xs text-gray-400">Entry</span>
                      </div>
                      <p className="text-lg font-bold text-white">
                        ${signal.entry_price.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <Shield className="w-3 h-3 text-red-400" />
                        <span className="text-xs text-gray-400">Stop Loss</span>
                      </div>
                      <p className="text-lg font-bold text-red-400">
                        ${signal.stop_loss.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <ArrowUpRight className="w-3 h-3 text-green-400" />
                        <span className="text-xs text-gray-400">Take Profit</span>
                      </div>
                      <p className="text-lg font-bold text-green-400">
                        ${signal.take_profit.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="flex items-center justify-between pt-4 border-t border-white/10">
                    <div className="flex items-center gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">R:R </span>
                        <span className="font-semibold text-amber-400">
                          1:{signal.risk_reward_ratio.toFixed(2)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Confidence </span>
                        <span className="font-semibold text-white">
                          {(signal.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(signal.timestamp), { addSuffix: true })}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Total Count */}
        {!isLoading && signals.length > 0 && (
          <div className="mt-6 text-center text-sm text-gray-400">
            Showing {signals.length} of {data?.total || 0} signals
          </div>
        )}
      </div>
    </div>
  );
}
