'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export interface Setting {
  id: number;
  key: string;
  category: string;
  value: string;
  value_type: string;
  default_value: string;
  description?: string;
  unit?: string;
  min_value?: number;
  max_value?: number;
  editable: boolean;
  requires_restart: boolean;
}

export interface SettingsByCategory {
  [category: string]: Setting[];
}

export function useSettings(category?: string) {
  return useQuery({
    queryKey: ['settings', category],
    queryFn: () => apiClient.getSettings(category),
  });
}

export function useSettingsByCategory() {
  return useQuery<SettingsByCategory>({
    queryKey: ['settings', 'by-category'],
    queryFn: () => apiClient.getSettingsByCategory(),
  });
}

export function useSetting(key: string) {
  return useQuery<Setting>({
    queryKey: ['setting', key],
    queryFn: () => apiClient.getSetting(key),
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      key,
      value,
      modifiedBy = 'admin',
    }: {
      key: string;
      value: any;
      modifiedBy?: string;
    }) => apiClient.updateSetting(key, value, modifiedBy),
    onSuccess: (data) => {
      // Invalidate all settings queries
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['setting', data.key] });

      if (data.requires_restart) {
        toast.warning('Setting updated', {
          description: 'Service restart required for changes to take effect.',
        });
      } else {
        toast.success('Setting updated successfully');
      }
    },
    onError: (error: any) => {
      toast.error('Failed to update setting', {
        description: error?.response?.data?.detail || error.message,
      });
    },
  });
}

export function useBulkUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      settings,
      modifiedBy = 'admin',
    }: {
      settings: Record<string, any>;
      modifiedBy?: string;
    }) => apiClient.bulkUpdateSettings(settings, modifiedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update settings', {
        description: error?.response?.data?.detail || error.message,
      });
    },
  });
}

export function useResetSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      key,
      modifiedBy = 'admin',
    }: {
      key: string;
      modifiedBy?: string;
    }) => apiClient.resetSetting(key, modifiedBy),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['setting', data.key] });
      toast.success('Setting reset to default');
    },
    onError: (error: any) => {
      toast.error('Failed to reset setting', {
        description: error?.response?.data?.detail || error.message,
      });
    },
  });
}

export function useServiceStatus() {
  return useQuery({
    queryKey: ['service-status'],
    queryFn: () => apiClient.getServiceStatus(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}
