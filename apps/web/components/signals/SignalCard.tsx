'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Signal } from '@/lib/hooks/useSignals';
import { TrendingUpIcon, TrendingDownIcon, ClockIcon } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface SignalCardProps {
  signal: Signal;
  onClick?: () => void;
}

export function SignalCard({ signal, onClick }: SignalCardProps) {
  const isLong = signal.direction === 'LONG';

  return (
    <Card
      className="p-3 sm:p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        {/* Left Section */}
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {/* Direction Icon */}
          <div
            className={`p-2 sm:p-3 rounded-lg shrink-0 ${
              isLong
                ? 'bg-green-100 dark:bg-green-900/30'
                : 'bg-red-100 dark:bg-red-900/30'
            }`}
          >
            {isLong ? (
              <TrendingUpIcon className="w-5 h-5 sm:w-6 sm:h-6 text-green-600 dark:text-green-400" />
            ) : (
              <TrendingDownIcon className="w-5 h-5 sm:w-6 sm:h-6 text-red-600 dark:text-red-400" />
            )}
          </div>

          {/* Signal Info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <Badge variant={isLong ? 'default' : 'destructive'} className="text-xs">
                {signal.direction}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {signal.timeframe}
              </Badge>
              <span className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white">
                {signal.symbol}
              </span>
            </div>

            <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-2">
              {signal.strategy_name}
            </p>

            {/* Price Levels */}
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <p className="text-gray-500 dark:text-gray-400">Entry</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  ${signal.entry_price.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">SL</p>
                <p className="font-medium text-red-600 dark:text-red-400">
                  ${signal.stop_loss.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400">TP</p>
                <p className="font-medium text-green-600 dark:text-green-400">
                  ${signal.take_profit.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section */}
        <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-2 sm:gap-3">
          {/* Status Badge */}
          <Badge
            variant={
              signal.status === 'ACTIVE'
                ? 'default'
                : signal.status === 'CLOSED'
                ? 'secondary'
                : 'outline'
            }
            className="text-xs"
          >
            {signal.status}
          </Badge>

          {/* Metrics */}
          <div className="text-right">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              RR Ratio
            </div>
            <div className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white">
              1:{signal.risk_reward_ratio.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <ClockIcon className="w-3 h-3" />
          <span>{formatDistanceToNow(new Date(signal.timestamp), { addSuffix: true })}</span>
        </div>
        <div>
          Confidence: <span className="font-medium">{(signal.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    </Card>
  );
}
