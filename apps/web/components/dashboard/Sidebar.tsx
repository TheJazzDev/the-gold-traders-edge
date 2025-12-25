'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboardIcon,
  SettingsIcon,
  TrendingUpIcon,
  BarChart3Icon,
  KeyIcon,
  CreditCardIcon,
  BellIcon,
  HomeIcon,
} from 'lucide-react';
import { useSubscription } from '@/lib/hooks/useSubscription';
import { Badge } from '@/components/ui/badge';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  requiredTier?: 'pro' | 'premium';
  badge?: string;
}

const navigation: NavItem[] = [
  {
    href: '/',
    label: 'Home',
    icon: HomeIcon,
  },
  {
    href: '/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboardIcon,
  },
  {
    href: '/dashboard/signals',
    label: 'Signals',
    icon: TrendingUpIcon,
  },
  {
    href: '/dashboard/settings',
    label: 'Settings',
    icon: SettingsIcon,
    requiredTier: 'pro',
  },
  {
    href: '/dashboard/analytics',
    label: 'Analytics',
    icon: BarChart3Icon,
    requiredTier: 'pro',
  },
  {
    href: '/dashboard/notifications',
    label: 'Notifications',
    icon: BellIcon,
    requiredTier: 'pro',
  },
  {
    href: '/dashboard/api-keys',
    label: 'API Keys',
    icon: KeyIcon,
    requiredTier: 'premium',
  },
  {
    href: '/dashboard/subscription',
    label: 'Subscription',
    icon: CreditCardIcon,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { tier, hasFeature } = useSubscription();

  return (
    <aside className="w-64 shrink-0 border-r bg-gray-50/50 dark:bg-gray-900/50">
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="p-4 sm:p-6 border-b">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <TrendingUpIcon className="w-5 h-5 text-white" />
            </div>
            <div className="hidden sm:block">
              <h2 className="text-base font-bold text-gray-900 dark:text-white">
                Gold Trader
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                {tier} Plan
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 sm:p-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            const isLocked =
              item.requiredTier &&
              !hasFeature(
                item.requiredTier === 'premium' ? 'apiAccess' : 'autoTrading'
              );

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100'
                    : isLocked
                    ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
                {...(isLocked && {
                  onClick: (e) => e.preventDefault(),
                })}
              >
                <div className="flex items-center space-x-2 sm:space-x-3">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="hidden sm:inline">{item.label}</span>
                </div>
                {isLocked && (
                  <Badge variant="secondary" className="text-xs px-1.5 py-0">
                    {item.requiredTier}
                  </Badge>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 sm:p-4 border-t">
          <div className="px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              v1.0.0 • Running
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
