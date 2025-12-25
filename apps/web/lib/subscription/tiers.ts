/**
 * Subscription Tiers and Feature Access
 *
 * Centralized configuration for subscription tiers and their permissions.
 * All feature gates should reference this file.
 */

export enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  PREMIUM = 'premium'
}

export interface TierFeatures {
  // Signals
  signalHistoryDays: number;
  realTimeAlerts: boolean;
  signalFiltering: boolean;

  // Trading
  autoTrading: boolean;
  multiAccount: boolean;
  copyTrading: boolean;

  // Settings & Control
  riskRange: [number, number]; // [min, max] percentage
  maxPositionsRange: [number, number];
  strategyControl: 'none' | 'preset' | 'custom';
  timeframeControl: boolean;
  dailyLossLimit: boolean;
  weeklyLossLimit: boolean;

  // Analytics
  basicStats: boolean;
  performanceCharts: boolean;
  advancedMetrics: boolean;
  customDateRanges: boolean;

  // Notifications
  emailAlerts: boolean;
  telegramBot: boolean;
  webhooks: boolean;
  smsAlerts: boolean;

  // API Access
  apiAccess: boolean;
  apiRateLimit: number; // requests per hour

  // Support
  emailSupport: boolean;
  prioritySupport: boolean;

  // Limits
  maxSignalsPerMonth: number;
}

export const TIER_FEATURES: Record<SubscriptionTier, TierFeatures> = {
  [SubscriptionTier.FREE]: {
    // Signals
    signalHistoryDays: 7,
    realTimeAlerts: false,
    signalFiltering: false,

    // Trading
    autoTrading: false,
    multiAccount: false,
    copyTrading: false,

    // Settings & Control
    riskRange: [0, 0], // No control
    maxPositionsRange: [0, 0], // No control
    strategyControl: 'none',
    timeframeControl: false,
    dailyLossLimit: false,
    weeklyLossLimit: false,

    // Analytics
    basicStats: true,
    performanceCharts: false,
    advancedMetrics: false,
    customDateRanges: false,

    // Notifications
    emailAlerts: false,
    telegramBot: false,
    webhooks: false,
    smsAlerts: false,

    // API Access
    apiAccess: false,
    apiRateLimit: 0,

    // Support
    emailSupport: false,
    prioritySupport: false,

    // Limits
    maxSignalsPerMonth: 50,
  },

  [SubscriptionTier.PRO]: {
    // Signals
    signalHistoryDays: -1, // Unlimited
    realTimeAlerts: true,
    signalFiltering: true,

    // Trading
    autoTrading: true,
    multiAccount: false,
    copyTrading: false,

    // Settings & Control
    riskRange: [0.5, 2.0], // Limited range
    maxPositionsRange: [1, 5],
    strategyControl: 'preset',
    timeframeControl: false,
    dailyLossLimit: true,
    weeklyLossLimit: true,

    // Analytics
    basicStats: true,
    performanceCharts: true,
    advancedMetrics: false,
    customDateRanges: false,

    // Notifications
    emailAlerts: true,
    telegramBot: true,
    webhooks: false,
    smsAlerts: false,

    // API Access
    apiAccess: false,
    apiRateLimit: 0,

    // Support
    emailSupport: true,
    prioritySupport: false,

    // Limits
    maxSignalsPerMonth: -1, // Unlimited
  },

  [SubscriptionTier.PREMIUM]: {
    // Signals
    signalHistoryDays: -1, // Unlimited
    realTimeAlerts: true,
    signalFiltering: true,

    // Trading
    autoTrading: true,
    multiAccount: true,
    copyTrading: true,

    // Settings & Control
    riskRange: [0.1, 10.0], // Full range
    maxPositionsRange: [1, 20],
    strategyControl: 'custom',
    timeframeControl: true,
    dailyLossLimit: true,
    weeklyLossLimit: true,

    // Analytics
    basicStats: true,
    performanceCharts: true,
    advancedMetrics: true,
    customDateRanges: true,

    // Notifications
    emailAlerts: true,
    telegramBot: true,
    webhooks: true,
    smsAlerts: true,

    // API Access
    apiAccess: true,
    apiRateLimit: 1000,

    // Support
    emailSupport: true,
    prioritySupport: true,

    // Limits
    maxSignalsPerMonth: -1, // Unlimited
  },
};

export const TIER_PRICING = {
  [SubscriptionTier.FREE]: {
    monthly: 0,
    yearly: 0,
    name: 'Free',
    description: 'View signals and learn',
    popular: false,
  },
  [SubscriptionTier.PRO]: {
    monthly: 49,
    yearly: 490, // ~2 months free
    name: 'Pro',
    description: 'Auto-trade with basic customization',
    popular: true,
  },
  [SubscriptionTier.PREMIUM]: {
    monthly: 149,
    yearly: 1490, // ~2 months free
    name: 'Premium',
    description: 'Full control and advanced features',
    popular: false,
  },
};

/**
 * Check if a tier has access to a specific feature
 */
export function hasFeatureAccess(
  userTier: SubscriptionTier,
  feature: keyof TierFeatures
): boolean {
  const features = TIER_FEATURES[userTier];
  const value = features[feature];

  // Boolean features
  if (typeof value === 'boolean') {
    return value;
  }

  // Numeric features (-1 means unlimited)
  if (typeof value === 'number') {
    return value !== 0;
  }

  // String features
  if (typeof value === 'string') {
    return value !== 'none';
  }

  // Array features (ranges)
  if (Array.isArray(value)) {
    return value[1] > 0; // Has maximum value
  }

  return false;
}

/**
 * Check if user can upgrade to a higher tier
 */
export function canUpgradeTo(
  currentTier: SubscriptionTier,
  targetTier: SubscriptionTier
): boolean {
  const tiers = [SubscriptionTier.FREE, SubscriptionTier.PRO, SubscriptionTier.PREMIUM];
  const currentIndex = tiers.indexOf(currentTier);
  const targetIndex = tiers.indexOf(targetTier);

  return targetIndex > currentIndex;
}

/**
 * Get the next tier for upgrade
 */
export function getNextTier(currentTier: SubscriptionTier): SubscriptionTier | null {
  switch (currentTier) {
    case SubscriptionTier.FREE:
      return SubscriptionTier.PRO;
    case SubscriptionTier.PRO:
      return SubscriptionTier.PREMIUM;
    case SubscriptionTier.PREMIUM:
      return null; // Already at highest tier
    default:
      return null;
  }
}

/**
 * Get feature comparison for pricing page
 */
export function getFeatureComparison() {
  return {
    'Signal Features': [
      { name: 'Signal History', free: '7 days', pro: 'Unlimited', premium: 'Unlimited' },
      { name: 'Real-time Alerts', free: false, pro: true, premium: true },
      { name: 'Signal Filtering', free: false, pro: true, premium: true },
    ],
    'Trading': [
      { name: 'Manual Trading', free: true, pro: true, premium: true },
      { name: 'Auto-Trading', free: false, pro: true, premium: true },
      { name: 'Multi-Account', free: false, pro: false, premium: true },
      { name: 'Copy Trading', free: false, pro: false, premium: true },
    ],
    'Risk Management': [
      { name: 'Risk Control', free: 'None', pro: '0.5% - 2%', premium: '0.1% - 10%' },
      { name: 'Max Positions', free: 'N/A', pro: '1 - 5', premium: '1 - 20' },
      { name: 'Strategy Selection', free: false, pro: 'Presets', premium: 'Custom' },
      { name: 'Timeframe Control', free: false, pro: false, premium: true },
    ],
    'Analytics': [
      { name: 'Basic Stats', free: true, pro: true, premium: true },
      { name: 'Performance Charts', free: false, pro: true, premium: true },
      { name: 'Advanced Metrics', free: false, pro: false, premium: true },
      { name: 'Custom Date Ranges', free: false, pro: false, premium: true },
    ],
    'Notifications': [
      { name: 'Email Alerts', free: false, pro: true, premium: true },
      { name: 'Telegram Bot', free: false, pro: true, premium: true },
      { name: 'Webhooks', free: false, pro: false, premium: true },
    ],
    'Advanced': [
      { name: 'API Access', free: false, pro: false, premium: true },
      { name: 'Priority Support', free: false, pro: false, premium: true },
    ],
  };
}
