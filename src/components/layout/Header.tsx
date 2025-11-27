"use client";

import { useState } from "react";
import { Bell, Settings, TrendingUp, Menu, X } from "lucide-react";
import { useNotificationStore, useMarketStore } from "@/store";
import { formatPrice, formatPercent } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { unreadCount } = useNotificationStore();
  const { currentPrice, isConnected } = useMarketStore();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-secondary-800/50 bg-secondary-950/80 backdrop-blur-xl">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <a href="/" className="flex items-center gap-3 group">
              <div className="relative w-10 h-10 flex items-center justify-center">
                <div className="absolute inset-0 gold-gradient rounded-lg opacity-20 group-hover:opacity-30 transition-opacity" />
                <TrendingUp className="w-6 h-6 text-primary-400" />
              </div>
              <div className="hidden sm:block">
                <h1 className="font-display font-bold text-lg gold-text">
                  The Gold Trader&apos;s Edge
                </h1>
                <p className="text-[10px] text-secondary-400 uppercase tracking-widest">
                  Mindset • Risk • Execution
                </p>
              </div>
            </a>

            <nav className="hidden md:flex items-center gap-6">
              <a
                href="/"
                className="text-sm font-medium text-white hover:text-primary-400 transition-colors"
              >
                Dashboard
              </a>
              <a
                href="/signals"
                className="text-sm font-medium text-secondary-300 hover:text-primary-400 transition-colors"
              >
                Signals
              </a>
              <a
                href="/analytics"
                className="text-sm font-medium text-secondary-300 hover:text-primary-400 transition-colors"
              >
                Analytics
              </a>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {currentPrice && (
              <div className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-xl bg-secondary-900/50 border border-secondary-700/50">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-secondary-400">XAUUSD</span>
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full",
                      isConnected ? "bg-profit animate-pulse" : "bg-loss"
                    )}
                  />
                </div>
                <span className="font-mono font-bold text-white">
                  {formatPrice(currentPrice.price)}
                </span>
                <span
                  className={cn(
                    "text-xs font-medium",
                    currentPrice.change >= 0 ? "text-profit" : "text-loss"
                  )}
                >
                  {formatPercent(currentPrice.changePercent)}
                </span>
              </div>
            )}

            <button
              className="relative p-2 rounded-lg hover:bg-secondary-800 transition-colors"
              aria-label="Notifications"
            >
              <Bell className="w-5 h-5 text-secondary-300" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center rounded-full bg-primary-500 text-secondary-950 text-xs font-bold">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            <button
              className="p-2 rounded-lg hover:bg-secondary-800 transition-colors"
              aria-label="Settings"
            >
              <Settings className="w-5 h-5 text-secondary-300" />
            </button>

            <button
              className="md:hidden p-2 rounded-lg hover:bg-secondary-800 transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Menu"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-secondary-300" />
              ) : (
                <Menu className="w-5 h-5 text-secondary-300" />
              )}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <nav className="md:hidden py-4 border-t border-secondary-800/50">
            <div className="flex flex-col gap-2">
              <a
                href="/"
                className="px-4 py-2 text-sm font-medium text-white hover:bg-secondary-800 rounded-lg transition-colors"
              >
                Dashboard
              </a>
              <a
                href="/signals"
                className="px-4 py-2 text-sm font-medium text-secondary-300 hover:bg-secondary-800 rounded-lg transition-colors"
              >
                Signals
              </a>
              <a
                href="/analytics"
                className="px-4 py-2 text-sm font-medium text-secondary-300 hover:bg-secondary-800 rounded-lg transition-colors"
              >
                Analytics
              </a>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}
