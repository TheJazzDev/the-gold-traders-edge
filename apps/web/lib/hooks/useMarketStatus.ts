import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface MarketStatus {
  is_open: boolean;
  reason: string;
  current_time: string;
  timezone: string;
  next_open?: string;
  next_close?: string;
  time_until_event?: string;
  market_hours: {
    description: string;
    open: string;
    close: string;
  };
}

export function useMarketStatus() {
  return useQuery<MarketStatus>({
    queryKey: ['marketStatus'],
    queryFn: () => apiClient.getMarketStatus(),
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000, // Consider data stale after 30 seconds
  });
}
