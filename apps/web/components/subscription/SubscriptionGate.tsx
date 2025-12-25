'use client';

import { useSubscription } from '@/lib/hooks/useSubscription';
import { SubscriptionTier } from '@/lib/subscription/tiers';
import { UpgradePrompt } from './UpgradePrompt';

interface SubscriptionGateProps {
  children: React.ReactNode;
  requiredTier: SubscriptionTier;
  feature: string;
  fallback?: React.ReactNode;
}

export function SubscriptionGate({
  children,
  requiredTier,
  feature,
  fallback,
}: SubscriptionGateProps) {
  const { tier, canUpgrade } = useSubscription();

  // Check if user has access
  const hasAccess = canUpgrade(requiredTier) === false || tier === requiredTier;

  if (!hasAccess) {
    return (
      fallback || (
        <UpgradePrompt
          currentTier={tier}
          requiredTier={requiredTier}
          feature={feature}
        />
      )
    );
  }

  return <>{children}</>;
}
