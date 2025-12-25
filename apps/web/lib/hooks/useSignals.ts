'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface Signal {
  id: string;
  timestamp: string;
  symbol: string;
  timeframe: string;
  strategy_name: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  risk_pips: number;
  reward_pips: number;
  risk_reward_ratio: number;
  status: 'PENDING' | 'ACTIVE' | 'CLOSED' | 'CANCELLED';
  notes?: string;
  created_at: string;
}

export interface SignalsResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export function useSignals(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  strategy?: string;
  timeframe?: string;
}) {
  return useQuery<SignalsResponse>({
    queryKey: ['signals', params],
    queryFn: () => apiClient.getSignals(params),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useSignal(id: string) {
  return useQuery<Signal>({
    queryKey: ['signal', id],
    queryFn: () => apiClient.getSignal(id),
    enabled: !!id,
  });
}

export function useRecentSignals(limit: number = 10) {
  return useSignals({ limit, offset: 0 });
}
