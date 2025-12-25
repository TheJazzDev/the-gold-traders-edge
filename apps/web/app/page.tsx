'use client';

import Link from 'next/link';
import {
  TrendingUp,
  Zap,
  Shield,
  BarChart3,
  ChevronRight,
  CheckCircle2,
  ArrowUpRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-amber-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-orange-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Navigation */}
      <nav className="relative border-b border-white/10 bg-slate-950/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Gold Trader's Edge</span>
            </div>
            <div className="flex items-center gap-4">
              <Link href="/signals">
                <Button variant="ghost" className="text-white hover:bg-white/10">
                  Live Signals
                </Button>
              </Link>
              <Link href="/user">
                <Button className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700">
                  Dashboard
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm mb-6">
              <Zap className="w-4 h-4" />
              <span>76% Win Rate • 3.31x Profit Factor</span>
            </div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white mb-6">
              Professional
              <span className="block mt-2 bg-gradient-to-r from-amber-400 via-orange-500 to-amber-400 bg-clip-text text-transparent">
                Gold Trading Signals
              </span>
            </h1>

            <p className="text-xl text-gray-400 mb-10">
              AI-powered, multi-timeframe analysis delivering high-probability XAUUSD signals
              in real-time. Backed by proven strategies with exceptional performance.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/signals">
                <Button size="lg" className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white h-12 px-8">
                  View Live Signals
                  <ArrowUpRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <Link href="/user">
                <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10 h-12 px-8">
                  Access Dashboard
                </Button>
              </Link>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-3xl font-bold text-amber-400 mb-2">76%</div>
              <div className="text-gray-400">Win Rate</div>
              <div className="text-xs text-gray-500 mt-1">Momentum Equilibrium Strategy</div>
            </Card>
            <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-3xl font-bold text-amber-400 mb-2">5/15/30m/1H</div>
              <div className="text-gray-400">Multi-Timeframe</div>
              <div className="text-xs text-gray-500 mt-1">Real-time analysis across 6 timeframes</div>
            </Card>
            <Card className="p-6 bg-white/5 border-white/10 backdrop-blur-xl">
              <div className="text-3xl font-bold text-amber-400 mb-2">24/7</div>
              <div className="text-gray-400">Live Monitoring</div>
              <div className="text-xs text-gray-500 mt-1">Continuous signal generation</div>
            </Card>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="relative py-20 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Powerful Features</h2>
            <p className="text-xl text-gray-400">Everything you need for successful gold trading</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="p-8 bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-6">
                <TrendingUp className="w-6 h-6 text-amber-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Real-Time Signals</h3>
              <p className="text-gray-400 mb-6">
                Get instant alerts when high-probability setups emerge across multiple timeframes.
              </p>
              <ul className="space-y-2">
                {['Entry price', 'Stop loss', 'Take profit', 'Risk/Reward ratio'].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle2 className="w-4 h-4 text-amber-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-8 bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-6">
                <Shield className="w-6 h-6 text-amber-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Risk Management</h3>
              <p className="text-gray-400 mb-6">
                Built-in risk controls to protect your capital with customizable parameters.
              </p>
              <ul className="space-y-2">
                {['Position sizing', 'Max daily loss', 'Max positions', 'Auto-trading controls'].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle2 className="w-4 h-4 text-amber-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-8 bg-white/5 border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center mb-6">
                <BarChart3 className="w-6 h-6 text-amber-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Performance Analytics</h3>
              <p className="text-gray-400 mb-6">
                Track your results with detailed performance metrics and backtested strategies.
              </p>
              <ul className="space-y-2">
                {['Win rate tracking', 'Profit factor', 'Strategy comparison', 'Historical data'].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle2 className="w-4 h-4 text-amber-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Card className="p-12 bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20 backdrop-blur-xl">
            <h2 className="text-4xl font-bold text-white mb-6">
              Ready to Transform Your Trading?
            </h2>
            <p className="text-xl text-gray-300 mb-8">
              Join traders using our proven strategies to capture gold market opportunities.
            </p>
            <Link href="/user">
              <Button size="lg" className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 h-14 px-10 text-lg">
                Get Started Now
                <ChevronRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-gray-400 text-sm">
              © 2024 Gold Trader's Edge. All rights reserved.
            </div>
            <div className="flex gap-6">
              <Link href="/signals" className="text-gray-400 hover:text-white text-sm transition-colors">
                Signals
              </Link>
              <Link href="/user" className="text-gray-400 hover:text-white text-sm transition-colors">
                Dashboard
              </Link>
              <Link href="/admin" className="text-gray-400 hover:text-white text-sm transition-colors">
                Admin
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
