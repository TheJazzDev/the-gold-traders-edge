'use client';

import { useServiceStatus } from '@/lib/hooks/useSettings';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BellIcon, UserIcon, MenuIcon } from 'lucide-react';

interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  const { data: serviceStatus } = useServiceStatus();

  return (
    <header className="border-b bg-white dark:bg-gray-950">
      <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white truncate">
            {title}
          </h1>
          {description && (
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-0.5 sm:mt-1">
              {description}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-4 ml-4">
          {/* Service Status */}
          <div className="hidden sm:flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                serviceStatus?.status === 'running'
                  ? 'bg-green-500'
                  : 'bg-red-500'
              }`}
            />
            <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
              {serviceStatus?.status === 'running' ? 'Service Running' : 'Service Stopped'}
            </span>
          </div>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <BellIcon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </Button>

          {/* User Menu */}
          <Button variant="ghost" size="icon">
            <UserIcon className="w-4 h-4 sm:w-5 sm:h-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
