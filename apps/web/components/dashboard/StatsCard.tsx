'use client';

import { Card } from '@/components/ui/card';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
  loading?: boolean;
  className?: string;
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  loading,
  className,
}: StatsCardProps) {
  if (loading) {
    return (
      <Card className={cn('p-4 sm:p-6', className)}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
          <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-3/4" />
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('p-4 sm:p-6', className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs sm:text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-1 sm:mt-2 text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          {trend && (
            <p
              className={cn(
                'mt-1 sm:mt-2 text-xs sm:text-sm font-medium',
                trend.value > 0
                  ? 'text-green-600 dark:text-green-500'
                  : trend.value < 0
                  ? 'text-red-600 dark:text-red-500'
                  : 'text-gray-600 dark:text-gray-400'
              )}
            >
              {trend.value > 0 ? '+' : ''}
              {trend.value}% {trend.label}
            </p>
          )}
        </div>
        <div className="p-2 sm:p-3 rounded-lg bg-gray-100 dark:bg-gray-800">
          <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-gray-600 dark:text-gray-400" />
        </div>
      </div>
    </Card>
  );
}
