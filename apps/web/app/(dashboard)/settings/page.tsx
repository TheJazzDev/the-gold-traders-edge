'use client';

import { Header } from '@/components/dashboard/Header';
import { RiskManagementPanel } from '@/components/settings/RiskManagementPanel';
import { StrategySelector } from '@/components/settings/StrategySelector';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useSetting, useUpdateSetting } from '@/lib/hooks/useSettings';
import { useState, useEffect } from 'react';

export default function SettingsPage() {
  const { data: autoTradingSetting } = useSetting('auto_trading_enabled');
  const { data: dryRunSetting } = useSetting('dry_run_mode');
  const updateSetting = useUpdateSetting();

  const [autoTrading, setAutoTrading] = useState(false);
  const [dryRun, setDryRun] = useState(true);

  useEffect(() => {
    if (autoTradingSetting) {
      setAutoTrading(autoTradingSetting.value === 'true');
    }
  }, [autoTradingSetting]);

  useEffect(() => {
    if (dryRunSetting) {
      setDryRun(dryRunSetting.value === 'true');
    }
  }, [dryRunSetting]);

  const handleAutoTradingToggle = async (checked: boolean) => {
    setAutoTrading(checked);
    await updateSetting.mutateAsync({
      key: 'auto_trading_enabled',
      value: checked.toString(),
    });
  };

  const handleDryRunToggle = async (checked: boolean) => {
    setDryRun(checked);
    await updateSetting.mutateAsync({
      key: 'dry_run_mode',
      value: checked.toString(),
    });
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Settings"
        description="Configure your trading parameters and preferences"
      />

      <div className="flex-1 p-4 sm:p-6 space-y-4 sm:space-y-6 overflow-y-auto">
        {/* Trading Settings */}
        <Card className="p-4 sm:p-6">
          <div className="space-y-4 sm:space-y-6">
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                Trading Settings
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                Control auto-trading and execution modes
              </p>
            </div>

            <div className="space-y-4">
              {/* Auto-Trading Toggle */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-4 rounded-lg border gap-2">
                <div className="flex-1">
                  <Label htmlFor="auto-trading" className="text-sm sm:text-base font-medium">
                    Auto-Trading
                  </Label>
                  <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Automatically execute signals on your MT5 account
                  </p>
                </div>
                <Switch
                  id="auto-trading"
                  checked={autoTrading}
                  onCheckedChange={handleAutoTradingToggle}
                />
              </div>

              {/* Dry Run Mode */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-4 rounded-lg border gap-2">
                <div className="flex-1">
                  <Label htmlFor="dry-run" className="text-sm sm:text-base font-medium">
                    Dry Run Mode
                  </Label>
                  <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Simulate trades without executing them (testing mode)
                  </p>
                </div>
                <Switch
                  id="dry-run"
                  checked={dryRun}
                  onCheckedChange={handleDryRunToggle}
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Risk Management */}
        <RiskManagementPanel />

        {/* Strategy Selection */}
        <StrategySelector />
      </div>
    </div>
  );
}
