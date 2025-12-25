'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  SubscriptionTier,
  TierFeatures,
  TIER_FEATURES,
  hasFeatureAccess,
  canUpgradeTo,
  getNextTier,
} from '@/lib/subscription/tiers';

interface SubscriptionState {
  tier: SubscriptionTier;
  features: TierFeatures;
  setTier: (tier: SubscriptionTier) => void;
  hasFeature: (feature: keyof TierFeatures) => boolean;
  canUpgrade: (targetTier: SubscriptionTier) => boolean;
  nextTier: () => SubscriptionTier | null;
}

export const useSubscription = create<SubscriptionState>()(
  persist(
    (set, get) => ({
      tier: SubscriptionTier.FREE,
      features: TIER_FEATURES[SubscriptionTier.FREE],

      setTier: (tier: SubscriptionTier) =>
        set({
          tier,
          features: TIER_FEATURES[tier],
        }),

      hasFeature: (feature: keyof TierFeatures) => {
        const { tier } = get();
        return hasFeatureAccess(tier, feature);
      },

      canUpgrade: (targetTier: SubscriptionTier) => {
        const { tier } = get();
        return canUpgradeTo(tier, targetTier);
      },

      nextTier: () => {
        const { tier } = get();
        return getNextTier(tier);
      },
    }),
    {
      name: 'subscription-storage',
    }
  )
);
