'use client';

import { useSettings, useSettingsByCategory, useUpdateSetting, useServiceStatus } from '@/lib/hooks/useSettings';
import { useRecentSignals } from '@/lib/hooks/useSignals';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Home,
  TrendingUp,
  Settings,
  BarChart3,
  Activity,
  Zap,
  Shield,
  Play,
  Pause,
  CheckCircle2,
} from 'lucide-react';

export default function UserDashboard() {
  const { data: serviceStatus } = useServiceStatus();
  const { data: settingsByCategory } = useSettingsByCategory();
  const { data: recentSignals } = useRecentSignals(5);
  const updateSetting = useUpdateSetting();

  const [autoTrading, setAutoTrading] = useState(false);
  const [maxRisk, setMaxRisk] = useState(1.0);
  const [maxPositions, setMaxPositions] = useState(3);

  const riskSettings = settingsByCategory?.risk_management || [];

  useEffect(() => {
    if (riskSettings.length > 0) {
      riskSettings.forEach((setting) => {
        if (setting.key === 'max_risk_per_trade') {
          setMaxRisk(parseFloat(setting.value));
        } else if (setting.key === 'max_positions') {
          setMaxPositions(parseInt(setting.value));
        } else if (setting.key === 'auto_trading_enabled') {
          setAutoTrading(setting.value === 'true');
        }
      });
    }
  }, [riskSettings]);

  const handleAutoTradingToggle = async (checked: boolean) => {
    setAutoTrading(checked);
    await updateSetting.mutateAsync({
      key: 'auto_trading_enabled',
      value: checked.toString(),
    });
  };

  const handleRiskSave = async () => {
    await Promise.all([
      updateSetting.mutateAsync({
        key: 'max_risk_per_trade',
        value: maxRisk.toString(),
      }),
      updateSetting.mutateAsync({
        key: 'max_positions',
        value: maxPositions.toString(),
      }),
    ]);
  };

  const signals = recentSignals?.signals || [];
  const activeSignals = signals.filter((s) => s.status === 'ACTIVE').length;
  const totalSignals = recentSignals?.total || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
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
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-white" />
                </div>
                <span className="text-white font-semibold hidden sm:block">User Dashboard</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/signals">
                <Button variant="outline" className="border-white/20 text-white hover:bg-white/10">
                  <Activity className="w-4 h-4 mr-2" />
                  All Signals
                </Button>
              </Link>
              <Link href="/admin">
                <Button variant="ghost" className="text-gray-400 hover:text-white hover:bg-white/10">
                  Admin
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
          <h1 className="text-4xl font-bold text-white mb-3">Trading Dashboard</h1>
          <p className="text-gray-400">Manage your signals, settings, and performance</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-amber-400" />
              </div>
              {serviceStatus?.status === 'running' ? (
                <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
                  Live
                </Badge>
              ) : (
                <Badge variant="secondary">Offline</Badge>
              )}
            </div>
            <p className="text-3xl font-bold text-white mb-1">{totalSignals}</p>
            <p className="text-sm text-gray-400">Total Signals</p>
          </Card>

          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center mb-4">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{activeSignals}</p>
            <p className="text-sm text-gray-400">Active Positions</p>
          </Card>

          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center mb-4">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{maxRisk}%</p>
            <p className="text-sm text-gray-400">Risk per Trade</p>
          </Card>

          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center mb-4">
              <Zap className="w-5 h-5 text-purple-400" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">76%</p>
            <p className="text-sm text-gray-400">Win Rate</p>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Auto-Trading Control */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Auto-Trading</h2>
              {autoTrading ? (
                <Play className="w-5 h-5 text-green-400" />
              ) : (
                <Pause className="w-5 h-5 text-gray-400" />
              )}
            </div>

            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 rounded-lg bg-black/20">
                <div>
                  <Label htmlFor="auto-trading" className="text-base font-medium text-white">
                    Enable Auto-Trading
                  </Label>
                  <p className="text-sm text-gray-400 mt-1">
                    Automatically execute signals on your MT5 account
                  </p>
                </div>
                <Switch
                  id="auto-trading"
                  checked={autoTrading}
                  onCheckedChange={handleAutoTradingToggle}
                />
              </div>

              {autoTrading && (
                <div className="p-4 rounded-lg border border-amber-500/20 bg-amber-500/5">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-400 mb-1">
                        Auto-Trading Active
                      </p>
                      <p className="text-xs text-gray-400">
                        Signals will be executed automatically based on your risk settings
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Risk Management */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Risk Settings</h2>
              <Shield className="w-5 h-5 text-blue-400" />
            </div>

            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-sm text-gray-300">Max Risk Per Trade</Label>
                  <span className="text-lg font-bold text-white">{maxRisk.toFixed(1)}%</span>
                </div>
                <Slider
                  value={[maxRisk]}
                  min={0.1}
                  max={10}
                  step={0.1}
                  onValueChange={([value]) => setMaxRisk(value)}
                  className="mb-2"
                />
                <p className="text-xs text-gray-500">Risk range: 0.1% - 10%</p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-sm text-gray-300">Max Concurrent Positions</Label>
                  <span className="text-lg font-bold text-white">{maxPositions}</span>
                </div>
                <Slider
                  value={[maxPositions]}
                  min={1}
                  max={20}
                  step={1}
                  onValueChange={([value]) => setMaxPositions(value)}
                  className="mb-2"
                />
                <p className="text-xs text-gray-500">Position range: 1 - 20</p>
              </div>

              <Button
                onClick={handleRiskSave}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700"
              >
                Save Settings
              </Button>
            </div>
          </Card>

          {/* Recent Signals */}
          <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl lg:col-span-2">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Recent Signals</h2>
              <Link href="/signals">
                <Button variant="outline" size="sm" className="border-white/20 text-white hover:bg-white/10">
                  View All
                </Button>
              </Link>
            </div>

            {signals.length === 0 ? (
              <div className="text-center py-12">
                <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">No signals yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {signals.map((signal) => (
                  <div
                    key={signal.id}
                    className="p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={signal.direction === 'LONG' ? 'default' : 'destructive'}
                          className="font-semibold"
                        >
                          {signal.direction}
                        </Badge>
                        <div>
                          <p className="text-sm font-medium text-white">
                            {signal.symbol} • {signal.timeframe.toUpperCase()}
                          </p>
                          <p className="text-xs text-gray-400">{signal.strategy_name}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-white">
                          ${signal.entry_price.toFixed(2)}
                        </p>
                        <p className="text-xs text-amber-400">
                          RR: 1:{signal.risk_reward_ratio.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
