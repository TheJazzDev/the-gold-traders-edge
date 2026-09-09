import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import type { ServiceStatus, SettingsByCategory, StrategyPerformance } from "@/lib/types";

export function useSettingsByCategory() {
  return useQuery<SettingsByCategory>({
    queryKey: ["settings", "by-category"],
    queryFn: () => apiClient.getSettingsByCategory(),
  });
}

export function useServiceStatus() {
  return useQuery<ServiceStatus>({
    queryKey: ["service-status"],
    queryFn: () => apiClient.getServiceStatus(),
    refetchInterval: 30000,
  });
}

export function useStrategies() {
  return useQuery<StrategyPerformance[]>({
    queryKey: ["strategies"],
    queryFn: () => apiClient.getStrategies(),
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      apiClient.updateSetting(key, value),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      queryClient.invalidateQueries({ queryKey: ["service-status"] });
      if (data.key === "enabled_strategies" || data.key === "enabled_forex_symbols") {
        queryClient.invalidateQueries({ queryKey: ["strategies"] });
      }
      toast.success(`Updated ${data.key}`, {
        description: data.requires_restart
          ? "This setting requires a service restart to take effect."
          : undefined,
      });
    },
    onError: (error: unknown) => {
      toast.error("Failed to update setting", {
        description: error instanceof Error ? error.message : undefined,
      });
    },
  });
}
