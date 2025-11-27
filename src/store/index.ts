import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Signal,
  MarketData,
  Notification,
  TimeFrame,
  AppSettings,
  TradeStats,
} from "@/types";

interface MarketState {
  currentPrice: MarketData | null;
  priceHistory: MarketData[];
  isConnected: boolean;
  lastUpdate: number;
  setCurrentPrice: (price: MarketData) => void;
  addPriceHistory: (price: MarketData) => void;
  setConnectionStatus: (status: boolean) => void;
}

interface SignalState {
  signals: Signal[];
  activeSignal: Signal | null;
  addSignal: (signal: Signal) => void;
  updateSignal: (id: string, updates: Partial<Signal>) => void;
  removeSignal: (id: string) => void;
  setActiveSignal: (signal: Signal | null) => void;
  getActiveSignals: () => Signal[];
  getPendingSignals: () => Signal[];
  getClosedSignals: () => Signal[];
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, "id" | "timestamp" | "read">) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

interface ChartState {
  timeframe: TimeFrame;
  showVolume: boolean;
  showSignals: boolean;
  showLevels: boolean;
  setTimeframe: (tf: TimeFrame) => void;
  toggleVolume: () => void;
  toggleSignals: () => void;
  toggleLevels: () => void;
}

interface SettingsState {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
}

export const useMarketStore = create<MarketState>((set, get) => ({
  currentPrice: null,
  priceHistory: [],
  isConnected: false,
  lastUpdate: 0,

  setCurrentPrice: (price) =>
    set({
      currentPrice: price,
      lastUpdate: Date.now(),
    }),

  addPriceHistory: (price) =>
    set((state) => ({
      priceHistory: [...state.priceHistory.slice(-1000), price],
    })),

  setConnectionStatus: (status) => set({ isConnected: status }),
}));

export const useSignalStore = create<SignalState>()(
  persist(
    (set, get) => ({
      signals: [],
      activeSignal: null,

      addSignal: (signal) =>
        set((state) => ({
          signals: [signal, ...state.signals],
        })),

      updateSignal: (id, updates) =>
        set((state) => ({
          signals: state.signals.map((s) =>
            s.id === id ? { ...s, ...updates, updatedAt: new Date() } : s
          ),
        })),

      removeSignal: (id) =>
        set((state) => ({
          signals: state.signals.filter((s) => s.id !== id),
        })),

      setActiveSignal: (signal) => set({ activeSignal: signal }),

      getActiveSignals: () =>
        get().signals.filter(
          (s) => s.status === "ACTIVE" || s.status === "TP1_HIT"
        ),

      getPendingSignals: () =>
        get().signals.filter((s) => s.status === "PENDING"),

      getClosedSignals: () =>
        get().signals.filter((s) =>
          ["TP1_HIT", "TP2_HIT", "SL_HIT", "CANCELLED", "EXPIRED"].includes(
            s.status
          )
        ),
    }),
    {
      name: "gold-signals-storage",
    }
  )
);

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      notifications: [],
      unreadCount: 0,

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: `notif-${Date.now()}`,
          timestamp: new Date(),
          read: false,
        };
        set((state) => ({
          notifications: [newNotification, ...state.notifications.slice(0, 49)],
          unreadCount: state.unreadCount + 1,
        }));

        if (typeof window !== "undefined" && "Notification" in window) {
          if (Notification.permission === "granted") {
            new Notification(notification.title, {
              body: notification.message,
              icon: "/logo.png",
            });
          }
        }
      },

      markAsRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
          unreadCount: Math.max(0, state.unreadCount - 1),
        })),

      markAllAsRead: () =>
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        })),

      clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
    }),
    {
      name: "gold-notifications-storage",
    }
  )
);

export const useChartStore = create<ChartState>((set) => ({
  timeframe: "1h",
  showVolume: false,
  showSignals: true,
  showLevels: true,

  setTimeframe: (tf) => set({ timeframe: tf }),
  toggleVolume: () => set((state) => ({ showVolume: !state.showVolume })),
  toggleSignals: () => set((state) => ({ showSignals: !state.showSignals })),
  toggleLevels: () => set((state) => ({ showLevels: !state.showLevels })),
}));

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: {
        notifications: {
          browser: true,
          email: false,
          telegram: false,
        },
        riskManagement: {
          maxRiskPercent: 2,
          minRiskReward: 1.5,
        },
        display: {
          theme: "dark",
          defaultTimeframe: "1h",
        },
      },
      updateSettings: (updates) =>
        set((state) => ({
          settings: { ...state.settings, ...updates },
        })),
    }),
    {
      name: "gold-settings-storage",
    }
  )
);

export function useTradeStats(): TradeStats {
  const signals = useSignalStore((state) => state.signals);
  const closedSignals = signals.filter((s) =>
    ["TP1_HIT", "TP2_HIT", "SL_HIT"].includes(s.status)
  );

  const wins = closedSignals.filter((s) =>
    ["TP1_HIT", "TP2_HIT"].includes(s.status)
  );
  const losses = closedSignals.filter((s) => s.status === "SL_HIT");

  const totalPips = closedSignals.reduce((sum, s) => sum + (s.pnlPips || 0), 0);
  const avgRR =
    closedSignals.length > 0
      ? closedSignals.reduce((sum, s) => sum + s.riskRewardRatio, 0) /
        closedSignals.length
      : 0;

  let currentStreak = 0;
  let streakType: "win" | "loss" = "win";

  for (const signal of closedSignals) {
    const isWin = ["TP1_HIT", "TP2_HIT"].includes(signal.status);
    if (currentStreak === 0) {
      streakType = isWin ? "win" : "loss";
      currentStreak = 1;
    } else if (
      (isWin && streakType === "win") ||
      (!isWin && streakType === "loss")
    ) {
      currentStreak++;
    } else {
      break;
    }
  }

  return {
    totalSignals: signals.length,
    activeSignals: signals.filter(
      (s) => s.status === "ACTIVE" || s.status === "PENDING"
    ).length,
    winRate: closedSignals.length > 0 ? (wins.length / closedSignals.length) * 100 : 0,
    totalPips,
    avgRiskReward: avgRR,
    profitFactor:
      losses.length > 0
        ? Math.abs(
            wins.reduce((sum, s) => sum + (s.pnlPips || 0), 0) /
              losses.reduce((sum, s) => sum + (s.pnlPips || 0), 0)
          )
        : wins.length > 0
        ? Infinity
        : 0,
    bestTrade: Math.max(...closedSignals.map((s) => s.pnlPips || 0), 0),
    worstTrade: Math.min(...closedSignals.map((s) => s.pnlPips || 0), 0),
    streak: {
      current: currentStreak,
      type: streakType,
    },
  };
}
