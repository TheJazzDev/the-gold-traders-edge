'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { useSettingsByCategory, useUpdateSetting } from '@/lib/hooks/useSettings';
import { useSubscription } from '@/lib/hooks/useSubscription';
import { Loader2Icon } from 'lucide-react';
import { SubscriptionGate } from '@/components/subscription/SubscriptionGate';
import { SubscriptionTier } from '@/lib/subscription/tiers';

export function RiskManagementPanel() {
  const { data: settingsByCategory, isLoading } = useSettingsByCategory();
  const updateSetting = useUpdateSetting();
  const { tier, features } = useSubscription();

  const riskSettings = settingsByCategory?.risk_management || [];

  // Local state for form values
  const [maxRisk, setMaxRisk] = useState(1.0);
  const [maxPositions, setMaxPositions] = useState(3);
  const [dailyLossLimit, setDailyLossLimit] = useState(5.0);
  const [weeklyLossLimit, setWeeklyLossLimit] = useState(10.0);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form values from settings
  useEffect(() => {
    if (riskSettings.length > 0) {
      riskSettings.forEach((setting) => {
        if (setting.key === 'max_risk_per_trade') {
          setMaxRisk(parseFloat(setting.value));
        } else if (setting.key === 'max_positions') {
          setMaxPositions(parseInt(setting.value));
        } else if (setting.key === 'max_daily_loss_percent') {
          setDailyLossLimit(parseFloat(setting.value));
        } else if (setting.key === 'max_weekly_loss_percent') {
          setWeeklyLossLimit(parseFloat(setting.value));
        }
      });
    }
  }, [riskSettings]);

  const handleSave = async () => {
    try {
      await Promise.all([
        updateSetting.mutateAsync({
          key: 'max_risk_per_trade',
          value: maxRisk.toString(),
        }),
        updateSetting.mutateAsync({
          key: 'max_positions',
          value: maxPositions.toString(),
        }),
        updateSetting.mutateAsync({
          key: 'max_daily_loss_percent',
          value: dailyLossLimit.toString(),
        }),
        updateSetting.mutateAsync({
          key: 'max_weekly_loss_percent',
          value: weeklyLossLimit.toString(),
        }),
      ]);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
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

  // Get tier-based limits
  const riskLimits = features.riskRange;
  const positionsLimits = features.maxPositionsRange;

  return (
    <SubscriptionGate requiredTier={SubscriptionTier.PRO} feature="Risk Management">
      <Card className="p-4 sm:p-6">
        <div className="space-y-4 sm:space-y-6">
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
              Risk Management
            </h3>
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
              Configure risk parameters for your trading strategy
            </p>
          </div>

          {/* Max Risk Per Trade */}
          <div className="space-y-2 sm:space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="max-risk" className="text-sm sm:text-base">
                Max Risk Per Trade
              </Label>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {maxRisk.toFixed(2)}%
              </span>
            </div>
            <Slider
              id="max-risk"
              value={[maxRisk]}
              min={riskLimits[0]}
              max={riskLimits[1]}
              step={0.1}
              onValueChange={([value]) => {
                setMaxRisk(value);
                setHasChanges(true);
              }}
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Range: {riskLimits[0]}% - {riskLimits[1]}%
              {tier === 'pro' && (
                <span className="text-amber-600 dark:text-amber-500 ml-2">
                  • Upgrade to Premium for up to 10%
                </span>
              )}
            </p>
          </div>

          {/* Max Positions */}
          <div className="space-y-2 sm:space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="max-positions" className="text-sm sm:text-base">
                Max Concurrent Positions
              </Label>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {maxPositions}
              </span>
            </div>
            <Slider
              id="max-positions"
              value={[maxPositions]}
              min={positionsLimits[0]}
              max={positionsLimits[1]}
              step={1}
              onValueChange={([value]) => {
                setMaxPositions(value);
                setHasChanges(true);
              }}
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Range: {positionsLimits[0]} - {positionsLimits[1]} positions
              {tier === 'pro' && (
                <span className="text-amber-600 dark:text-amber-500 ml-2">
                  • Upgrade to Premium for up to 20 positions
                </span>
              )}
            </p>
          </div>

          {/* Daily Loss Limit */}
          {features.dailyLossLimit && (
            <div className="space-y-2 sm:space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="daily-loss" className="text-sm sm:text-base">
                  Daily Loss Limit
                </Label>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {dailyLossLimit.toFixed(1)}%
                </span>
              </div>
              <Slider
                id="daily-loss"
                value={[dailyLossLimit]}
                min={1}
                max={20}
                step={0.5}
                onValueChange={([value]) => {
                  setDailyLossLimit(value);
                  setHasChanges(true);
                }}
                className="w-full"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Stop trading if daily loss exceeds this percentage
              </p>
            </div>
          )}

          {/* Weekly Loss Limit */}
          {features.weeklyLossLimit && (
            <div className="space-y-2 sm:space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="weekly-loss" className="text-sm sm:text-base">
                  Weekly Loss Limit
                </Label>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {weeklyLossLimit.toFixed(1)}%
                </span>
              </div>
              <Slider
                id="weekly-loss"
                value={[weeklyLossLimit]}
                min={2}
                max={40}
                step={1}
                onValueChange={([value]) => {
                  setWeeklyLossLimit(value);
                  setHasChanges(true);
                }}
                className="w-full"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Stop trading if weekly loss exceeds this percentage
              </p>
            </div>
          )}

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
