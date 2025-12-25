'use client';

import { useState } from 'react';
import { useSignals } from '@/lib/hooks/useSignals';
import { SignalCard } from './SignalCard';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2Icon } from 'lucide-react';

export function SignalsList() {
  const [status, setStatus] = useState<string>('all');
  const [timeframe, setTimeframe] = useState<string>('all');
  const [strategy, setStrategy] = useState<string>('all');
  const [limit] = useState(20);

  const { data, isLoading, error } = useSignals({
    limit,
    status: status === 'all' ? undefined : status,
    timeframe: timeframe === 'all' ? undefined : timeframe,
    strategy: strategy === 'all' ? undefined : strategy,
  });

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-sm text-red-600 dark:text-red-400">
            Failed to load signals
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {error.message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="CLOSED">Closed</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
          </SelectContent>
        </Select>

        <Select value={timeframe} onValueChange={setTimeframe}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Timeframe" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Timeframes</SelectItem>
            <SelectItem value="5m">5 Minutes</SelectItem>
            <SelectItem value="15m">15 Minutes</SelectItem>
            <SelectItem value="30m">30 Minutes</SelectItem>
            <SelectItem value="1h">1 Hour</SelectItem>
            <SelectItem value="4h">4 Hours</SelectItem>
            <SelectItem value="1d">1 Day</SelectItem>
          </SelectContent>
        </Select>

        <Select value={strategy} onValueChange={setStrategy}>
          <SelectTrigger className="w-full sm:w-[240px]">
            <SelectValue placeholder="Strategy" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Strategies</SelectItem>
            <SelectItem value="momentum_equilibrium">Momentum Equilibrium</SelectItem>
            <SelectItem value="london_session_breakout">London Breakout</SelectItem>
            <SelectItem value="golden_fibonacci">Golden Fibonacci</SelectItem>
            <SelectItem value="ath_retest">ATH Retest</SelectItem>
            <SelectItem value="order_block_retest">Order Block Retest</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Signals List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2Icon className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : data?.signals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No signals found matching your filters
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3 sm:space-y-4">
            {data?.signals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>

          {/* Pagination Info */}
          <div className="flex items-center justify-between pt-4 border-t text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            <p>
              Showing {data?.signals.length || 0} of {data?.total || 0} signals
            </p>
            {(data?.total || 0) > limit && (
              <Button variant="outline" size="sm">
                Load More
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
