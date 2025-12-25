'use client';

import { SubscriptionTier, TIER_PRICING, getNextTier } from '@/lib/subscription/tiers';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ArrowUpIcon, LockIcon } from 'lucide-react';
import Link from 'next/link';

interface UpgradePromptProps {
  currentTier: SubscriptionTier;
  requiredTier: SubscriptionTier;
  feature: string;
}

export function UpgradePrompt({
  currentTier,
  requiredTier,
  feature,
}: UpgradePromptProps) {
  const nextTier = getNextTier(currentTier);
  const targetTierInfo = TIER_PRICING[requiredTier];

  return (
    <Card className="p-6 sm:p-8 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 border-amber-200 dark:border-amber-800">
      <div className="flex flex-col items-center text-center space-y-4">
        <div className="p-3 rounded-full bg-amber-100 dark:bg-amber-900/30">
          <LockIcon className="w-6 h-6 sm:w-8 sm:h-8 text-amber-600 dark:text-amber-400" />
        </div>

        <div className="space-y-2">
          <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">
            {feature} - {targetTierInfo.name} Feature
          </h3>
          <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 max-w-md">
            Upgrade to <span className="font-semibold">{targetTierInfo.name}</span> to unlock{' '}
            {feature.toLowerCase()} and many more powerful features.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href="/dashboard/subscription/upgrade">
              <ArrowUpIcon className="w-4 h-4 mr-2" />
              Upgrade to {targetTierInfo.name}
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
            <Link href="/pricing">View All Plans</Link>
          </Button>
        </div>

        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-500">
          Starting at ${targetTierInfo.monthly}/month
        </p>
      </div>
    </Card>
  );
}
