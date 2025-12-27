'use client';

import { useMarketStatus } from '@/lib/hooks/useMarketStatus';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Clock, TrendingUp, Calendar } from 'lucide-react';

export function MarketStatus() {
  const { data: marketStatus, isLoading } = useMarketStatus();

  if (isLoading) {
    return (
      <Card className="p-3 sm:p-4 bg-white/5 border-white/10 backdrop-blur-xl animate-pulse">
        <div className="h-6 sm:h-8 bg-white/10 rounded" />
      </Card>
    );
  }

  if (!marketStatus) return null;

  const isOpen = marketStatus.is_open;

  return (
    <Card className="p-3 sm:p-4 bg-white/5 border-white/10 backdrop-blur-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div
            className={`w-2 h-2 sm:w-3 sm:h-3 rounded-full ${
              isOpen ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`}
          />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm sm:text-base font-semibold text-white">
                {isOpen ? 'Market Open' : 'Market Closed'}
              </h3>
              <Badge
                variant={isOpen ? 'default' : 'secondary'}
                className={`text-xs ${
                  isOpen
                    ? 'bg-green-500/20 text-green-400 border-green-500/40'
                    : 'bg-red-500/20 text-red-400 border-red-500/40'
                }`}
              >
                {isOpen ? 'LIVE' : 'CLOSED'}
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-gray-400 mt-0.5 sm:mt-1">
              {marketStatus.reason}
            </p>
          </div>
        </div>

        {/* Next Event */}
        <div className="flex flex-col sm:items-end gap-1">
          {marketStatus.time_until_event && (
            <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
              <Clock className="w-3 h-3 sm:w-4 sm:h-4 text-gray-400" />
              <span className="text-gray-400">
                {isOpen ? 'Closes in' : 'Opens in'}:
              </span>
              <span className="font-semibold text-amber-400">
                {marketStatus.time_until_event}
              </span>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            <span>{marketStatus.market_hours.description}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export function MarketStatusBadge() {
  const { data: marketStatus, isLoading } = useMarketStatus();

  if (isLoading || !marketStatus) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse" />
        <span className="text-xs sm:text-sm text-gray-400">Loading...</span>
      </div>
    );
  }

  const isOpen = marketStatus.is_open;

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-2 h-2 rounded-full ${
          isOpen ? 'bg-green-500 animate-pulse' : 'bg-red-500'
        }`}
      />
      <span className="text-xs sm:text-sm text-gray-400">
        {isOpen ? 'Market Open' : 'Market Closed'}
      </span>
    </div>
  );
}
