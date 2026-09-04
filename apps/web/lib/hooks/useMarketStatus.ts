import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { MarketStatus } from "@/lib/types";

export function useMarketStatus() {
  return useQuery<MarketStatus>({
    queryKey: ["marketStatus"],
    queryFn: () => apiClient.getMarketStatus(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}
