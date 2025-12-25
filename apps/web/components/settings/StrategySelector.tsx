'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSetting, useUpdateSetting } from '@/lib/hooks/useSettings';
import { useSubscription } from '@/lib/hooks/useSubscription';
import { Loader2Icon, InfoIcon } from 'lucide-react';
import { SubscriptionGate } from '@/components/subscription/SubscriptionGate';
import { SubscriptionTier } from '@/lib/subscription/tiers';

const STRATEGIES = [
  {
    key: 'momentum_equilibrium',
    name: 'Momentum Equilibrium',
    description: 'High-probability trend reversals at equilibrium zones',
    winRate: '76%',
    profitFactor: '3.31',
    badge: 'BEST',
  },
  {
    key: 'london_session_breakout',
    name: 'London Session Breakout',
    description: 'Capitalize on London session volatility',
    winRate: '58.8%',
    profitFactor: '2.74',
    badge: 'STRONG',
  },
  {
    key: 'golden_fibonacci',
    name: 'Golden Fibonacci',
    description: 'Fibonacci retracement entries with confluence',
    winRate: '52.6%',
    profitFactor: '1.44',
    badge: null,
  },
  {
    key: 'ath_retest',
    name: 'ATH Retest',
    description: 'All-time high retest entries',
    winRate: '38%',
    profitFactor: '1.30',
    badge: null,
  },
  {
    key: 'order_block_retest',
    name: 'Order Block Retest',
    description: 'Institutional smart money zones',
    winRate: 'New',
    profitFactor: 'TBD',
    badge: 'NEW',
  },
];

export function StrategySelector() {
  const { data: enabledStrategiesSetting, isLoading } = useSetting('enabled_strategies');
  const updateSetting = useUpdateSetting();
  const { tier, features } = useSubscription();

  const [enabledStrategies, setEnabledStrategies] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize from settings
  useEffect(() => {
    if (enabledStrategiesSetting?.value) {
      try {
        const strategies = JSON.parse(enabledStrategiesSetting.value);
        setEnabledStrategies(strategies);
      } catch (error) {
        console.error('Failed to parse enabled strategies:', error);
      }
    }
  }, [enabledStrategiesSetting]);

  const handleToggle = (strategyKey: string) => {
    setEnabledStrategies((prev) => {
      const newStrategies = prev.includes(strategyKey)
        ? prev.filter((s) => s !== strategyKey)
        : [...prev, strategyKey];
      setHasChanges(true);
      return newStrategies;
    });
  };

  const handleSave = async () => {
    try {
      await updateSetting.mutateAsync({
        key: 'enabled_strategies',
        value: JSON.stringify(enabledStrategies),
      });
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save strategies:', error);
    }
  };

  const handleEnableAll = () => {
    setEnabledStrategies(STRATEGIES.map((s) => s.key));
    setHasChanges(true);
  };

  const handleDisableAll = () => {
    setEnabledStrategies([]);
    setHasChanges(true);
  };

  if (isLoading) {
    return (
      <Card className="p-4 sm:p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2Icon className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </Card>
    );
  }

  const canCustomize = features.strategyControl === 'custom';

  return (
    <SubscriptionGate requiredTier={SubscriptionTier.PRO} feature="Strategy Selection">
      <Card className="p-4 sm:p-6">
        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                Trading Strategies
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                Enable or disable individual strategies
                {tier === 'pro' && (
                  <span className="text-amber-600 dark:text-amber-500 ml-2">
                    • Premium users can customize individual strategies
                  </span>
                )}
              </p>
            </div>
            {canCustomize && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleEnableAll}
                  className="text-xs sm:text-sm"
                >
                  Enable All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDisableAll}
                  className="text-xs sm:text-sm"
                >
                  Disable All
                </Button>
              </div>
            )}
          </div>

          <div className="space-y-3 sm:space-y-4">
            {STRATEGIES.map((strategy) => {
              const isEnabled = enabledStrategies.includes(strategy.key);

              return (
                <div
                  key={strategy.key}
                  className="flex flex-col sm:flex-row sm:items-start justify-between p-3 sm:p-4 rounded-lg border bg-gray-50 dark:bg-gray-900 gap-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm sm:text-base font-medium text-gray-900 dark:text-white">
                        {strategy.name}
                      </h4>
                      {strategy.badge && (
                        <Badge
                          variant={
                            strategy.badge === 'BEST'
                              ? 'default'
                              : strategy.badge === 'STRONG'
                              ? 'secondary'
                              : 'outline'
                          }
                          className="text-xs"
                        >
                          {strategy.badge}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-2">
                      {strategy.description}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs">
                      <span className="text-gray-500 dark:text-gray-400">
                        Win Rate:{' '}
                        <span className="font-medium text-green-600 dark:text-green-500">
                          {strategy.winRate}
                        </span>
                      </span>
                      <span className="text-gray-500 dark:text-gray-400">
                        Profit Factor:{' '}
                        <span className="font-medium text-gray-900 dark:text-white">
                          {strategy.profitFactor}
                        </span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 sm:gap-3 self-end sm:self-start">
                    <Switch
                      checked={isEnabled}
                      onCheckedChange={() => handleToggle(strategy.key)}
                      disabled={!canCustomize && tier === 'pro'}
                    />
                    <Label
                      htmlFor={strategy.key}
                      className="text-xs sm:text-sm text-gray-600 dark:text-gray-400"
                    >
                      {isEnabled ? 'Enabled' : 'Disabled'}
                    </Label>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Info Banner */}
          <div className="flex items-start gap-2 p-3 sm:p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
            <InfoIcon className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm text-blue-900 dark:text-blue-100">
              All strategies have been backtested with positive results. Disabling
              strategies will reduce signal frequency.
            </p>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-2 sm:pt-4 border-t">
            <Button
              onClick={handleSave}
              disabled={!hasChanges || updateSetting.isPending}
              className="w-full sm:w-auto"
            >
              {updateSetting.isPending && (
                <Loader2Icon className="w-4 h-4 mr-2 animate-spin" />
              )}
              Save Changes
            </Button>
          </div>
        </div>
      </Card>
    </SubscriptionGate>
  );
}
