import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { SignalsResponse } from "@/lib/types";

export function useSignals(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  strategy?: string;
  timeframe?: string;
}) {
  return useQuery<SignalsResponse>({
    queryKey: ["signals", params],
    queryFn: () => apiClient.getSignals(params),
    refetchInterval: 30000,
  });
}
