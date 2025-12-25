'use client';

import { useSettingsByCategory, useUpdateSetting, useServiceStatus } from '@/lib/hooks/useSettings';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Home,
  Settings,
  Server,
  Database,
  Zap,
  CheckCircle2,
  XCircle,
  Play,
  Square,
  RefreshCw,
} from 'lucide-react';

const STRATEGIES = [
  { key: 'momentum_equilibrium', name: 'Momentum Equilibrium', winRate: '76%', pf: '3.31' },
  { key: 'london_session_breakout', name: 'London Session Breakout', winRate: '58.8%', pf: '2.74' },
  { key: 'golden_fibonacci', name: 'Golden Fibonacci', winRate: '52.6%', pf: '1.44' },
  { key: 'ath_retest', name: 'ATH Retest', winRate: '38%', pf: '1.30' },
  { key: 'order_block_retest', name: 'Order Block Retest', winRate: 'New', pf: 'TBD' },
];

export default function AdminPanel() {
  const { data: settingsByCategory } = useSettingsByCategory();
  const { data: serviceStatus } = useServiceStatus();
  const updateSetting = useUpdateSetting();

  const [enabledStrategies, setEnabledStrategies] = useState<string[]>([]);
  const [autoTrading, setAutoTrading] = useState(false);
  const [dryRun, setDryRun] = useState(true);

  useEffect(() => {
    const tradingSettings = settingsByCategory?.trading || [];
    const strategiesSettings = settingsByCategory?.strategies || [];

    tradingSettings.forEach((setting) => {
      if (setting.key === 'auto_trading_enabled') {
        setAutoTrading(setting.value === 'true');
      } else if (setting.key === 'dry_run_mode') {
        setDryRun(setting.value === 'true');
      }
    });

    strategiesSettings.forEach((setting) => {
      if (setting.key === 'enabled_strategies') {
        try {
          setEnabledStrategies(JSON.parse(setting.value));
        } catch (e) {
          console.error('Failed to parse enabled strategies');
        }
      }
    });
  }, [settingsByCategory]);

  const handleStrategyToggle = async (strategyKey: string) => {
    const newStrategies = enabledStrategies.includes(strategyKey)
      ? enabledStrategies.filter((s) => s !== strategyKey)
      : [...enabledStrategies, strategyKey];

    setEnabledStrategies(newStrategies);
    await updateSetting.mutateAsync({
      key: 'enabled_strategies',
      value: JSON.stringify(newStrategies),
    });
  };

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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <nav className="relative border-b border-white/10 bg-slate-950/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" className="text-white hover:bg-white/10">
                  <Home className="w-4 h-4 mr-2" />
                  Home
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                  <Settings className="w-4 h-4 text-white" />
                </div>
                <span className="text-white font-semibold hidden sm:block">Admin Control Panel</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/user">
                <Button variant="outline" className="border-white/20 text-white hover:bg-white/10">
                  User Dashboard
                </Button>
              </Link>
              <Link href="/signals">
                <Button variant="ghost" className="text-gray-400 hover:text-white hover:bg-white/10">
                  Signals
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-3">System Control Panel</h1>
          <p className="text-gray-400">Manage strategies, trading settings, and system configuration</p>
        </div>

        {/* Service Status */}
        <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-blue-500/10 border-purple-500/20 backdrop-blur-xl mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                <Server className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-1">Service Status</h3>
                <p className="text-sm text-gray-400">
                  Data Feed: {serviceStatus?.data_feed_type || 'yahoo'} • Timeframes: {serviceStatus?.active_timeframes?.join(', ')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {serviceStatus?.status === 'running' ? (
                <>
                  <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
                    <Play className="w-3 h-3 mr-1" />
                    Running
                  </Badge>
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                </>
              ) : (
                <Badge variant="secondary">
                  <Square className="w-3 h-3 mr-1" />
                  Stopped
                </Badge>
              )}
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Trading Controls */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-amber-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Trading Controls</h2>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all">
                <div>
                  <Label htmlFor="auto-trading-admin" className="text-base font-medium text-white">
                    Auto-Trading
                  </Label>
                  <p className="text-sm text-gray-400 mt-1">
                    Execute signals automatically on MT5
                  </p>
                </div>
                <Switch
                  id="auto-trading-admin"
                  checked={autoTrading}
                  onCheckedChange={handleAutoTradingToggle}
                />
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all">
                <div>
                  <Label htmlFor="dry-run-admin" className="text-base font-medium text-white">
                    Dry Run Mode
                  </Label>
                  <p className="text-sm text-gray-400 mt-1">
                    Simulate trades without execution
                  </p>
                </div>
                <Switch
                  id="dry-run-admin"
                  checked={dryRun}
                  onCheckedChange={handleDryRunToggle}
                />
              </div>

              {autoTrading && !dryRun && (
                <div className="p-4 rounded-lg border border-red-500/20 bg-red-500/5">
                  <div className="flex items-start gap-2">
                    <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-400 mb-1">
                        Live Trading Enabled
                      </p>
                      <p className="text-xs text-gray-400">
                        Real trades will be executed. Ensure MT5 is configured correctly.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* System Info */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Database className="w-5 h-5 text-blue-400" />
              </div>
              <h2 className="text-xl font-bold text-white">System Information</h2>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-black/20">
                <span className="text-sm text-gray-400">Service Status</span>
                <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
                  {serviceStatus?.status || 'Unknown'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-black/20">
                <span className="text-sm text-gray-400">Auto-Trading</span>
                <Badge variant={autoTrading ? 'default' : 'secondary'}>
                  {autoTrading ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-black/20">
                <span className="text-sm text-gray-400">Mode</span>
                <Badge variant={dryRun ? 'secondary' : 'default'}>
                  {dryRun ? 'Dry Run' : 'Live'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-black/20">
                <span className="text-sm text-gray-400">Active Strategies</span>
                <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/40">
                  {enabledStrategies.length} / {STRATEGIES.length}
                </Badge>
              </div>
            </div>
          </Card>

          {/* Strategy Management */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl lg:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                </div>
                <h2 className="text-xl font-bold text-white">Strategy Management</h2>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="border-white/20 text-white hover:bg-white/10"
                  onClick={() => {
                    const allKeys = STRATEGIES.map(s => s.key);
                    setEnabledStrategies(allKeys);
                    updateSetting.mutateAsync({
                      key: 'enabled_strategies',
                      value: JSON.stringify(allKeys),
                    });
                  }}
                >
                  Enable All
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-white/20 text-white hover:bg-white/10"
                  onClick={() => {
                    setEnabledStrategies([]);
                    updateSetting.mutateAsync({
                      key: 'enabled_strategies',
                      value: JSON.stringify([]),
                    });
                  }}
                >
                  Disable All
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              {STRATEGIES.map((strategy) => {
                const isEnabled = enabledStrategies.includes(strategy.key);

                return (
                  <div
                    key={strategy.key}
                    className="flex items-center justify-between p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all"
                  >
                    <div className="flex items-center gap-4">
                      <Switch
                        checked={isEnabled}
                        onCheckedChange={() => handleStrategyToggle(strategy.key)}
                      />
                      <div>
                        <p className="text-base font-medium text-white mb-1">
                          {strategy.name}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-gray-400">
                          <span>Win Rate: <span className="text-green-400 font-medium">{strategy.winRate}</span></span>
                          <span>PF: <span className="text-amber-400 font-medium">{strategy.pf}</span></span>
                        </div>
                      </div>
                    </div>
                    {isEnabled ? (
                      <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        Disabled
                      </Badge>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
