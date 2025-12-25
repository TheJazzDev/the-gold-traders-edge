'use client';

import { Header } from '@/components/dashboard/Header';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { useRecentSignals } from '@/lib/hooks/useSignals';
import { useServiceStatus } from '@/lib/hooks/useSettings';
import {
  TrendingUpIcon,
  ActivityIcon,
  CheckCircleIcon,
  AlertCircleIcon,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

export default function DashboardPage() {
  const { data: signals, isLoading: signalsLoading } = useRecentSignals(5);
  const { data: serviceStatus, isLoading: statusLoading } = useServiceStatus();

  // Calculate stats
  const totalSignals = signals?.total || 0;
  const activeSignals =
    signals?.signals.filter((s) => s.status === 'ACTIVE').length || 0;
  const completedSignals =
    signals?.signals.filter((s) => s.status === 'CLOSED').length || 0;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dashboard"
        description="Monitor your trading signals and performance"
      />

      <div className="flex-1 p-4 sm:p-6 space-y-4 sm:space-y-6 overflow-y-auto">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <StatsCard
            title="Total Signals"
            value={totalSignals}
            icon={TrendingUpIcon}
            loading={signalsLoading}
          />
          <StatsCard
            title="Active Signals"
            value={activeSignals}
            icon={ActivityIcon}
            loading={signalsLoading}
          />
          <StatsCard
            title="Completed"
            value={completedSignals}
            icon={CheckCircleIcon}
            loading={signalsLoading}
          />
          <StatsCard
            title="Service Status"
            value={serviceStatus?.status === 'running' ? 'Running' : 'Stopped'}
            icon={AlertCircleIcon}
            loading={statusLoading}
          />
        </div>

        {/* Recent Signals */}
        <Card className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
              Recent Signals
            </h2>
            <a
              href="/dashboard/signals"
              className="text-xs sm:text-sm text-amber-600 hover:text-amber-700 dark:text-amber-500 dark:hover:text-amber-400"
            >
              View all →
            </a>
          </div>

          {signalsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="animate-pulse h-16 bg-gray-100 dark:bg-gray-800 rounded"
                />
              ))}
            </div>
          ) : signals?.signals.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">
              No signals yet. The service is running and will generate signals when
              conditions are met.
            </p>
          ) : (
            <div className="space-y-2 sm:space-y-3">
              {signals?.signals.map((signal) => (
                <div
                  key={signal.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-4 rounded-lg border bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors gap-2 sm:gap-0"
                >
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                    <Badge
                      variant={signal.direction === 'LONG' ? 'default' : 'destructive'}
                      className="shrink-0"
                    >
                      {signal.direction}
                    </Badge>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">
                        {signal.symbol} • {signal.timeframe}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {signal.strategy_name}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-4">
                    <div className="text-left sm:text-right">
                      <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white">
                        ${signal.entry_price.toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        RR: {signal.risk_reward_ratio.toFixed(2)}
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {signal.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Service Info */}
        {serviceStatus && (
          <Card className="p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Service Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Status
                </p>
                <p className="text-sm sm:text-base font-medium text-gray-900 dark:text-white mt-1">
                  {serviceStatus.status}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Auto-Trading
                </p>
                <p className="text-sm sm:text-base font-medium text-gray-900 dark:text-white mt-1">
                  {serviceStatus.auto_trading_enabled ? 'Enabled' : 'Disabled'}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Active Timeframes
                </p>
                <p className="text-sm sm:text-base font-medium text-gray-900 dark:text-white mt-1">
                  {serviceStatus.active_timeframes?.join(', ') || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Data Feed
                </p>
                <p className="text-sm sm:text-base font-medium text-gray-900 dark:text-white mt-1">
                  {serviceStatus.data_feed_type || 'yahoo'}
                </p>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
