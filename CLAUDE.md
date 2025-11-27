# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**The Gold Trader's Edge** is a professional XAUUSD (Gold) trading signal application that provides real-time technical analysis, pattern detection, and smart notifications for gold traders. The application uses a combination of technical indicators (RSI, MACD, EMA, ATR, Bollinger Bands) to generate high-probability trading signals with defined entry zones, stop losses, and take profit targets.

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: TailwindCSS v4 (Note: Uses new syntax like `shrink-0` instead of `flex-shrink-0`, `bg-linear-to-br` instead of `bg-gradient-to-br`)
- **Charts**: Lightweight Charts (TradingView)
- **State Management**: Zustand with persist middleware
- **Deployment**: Vercel

## Development Commands

```bash
# Development server (runs on port 4000)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Architecture & Key Concepts

### State Management (Zustand)

The application uses **5 primary Zustand stores** located in `src/store/index.ts`:

1. **`useMarketStore`** - Real-time price data and connection status
2. **`useSignalStore`** - Trading signals with persistence (localStorage: `gold-signals-storage`)
3. **`useNotificationStore`** - Browser notifications with persistence (localStorage: `gold-notifications-storage`)
4. **`useChartStore`** - Chart display preferences (timeframe, visibility toggles)
5. **`useSettingsStore`** - App settings with persistence (localStorage: `gold-settings-storage`)

Additionally, `useTradeStats()` is a computed hook that derives statistics from signals.

### Signal Generation Flow

The signal generation process follows this architecture:

1. **Data Fetching** (`src/services/market.ts`)
   - Fetches candle data from Finnhub API or generates simulated data if no API key
   - Symbol: `OANDA:XAU_USD`
   - Supports multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d, 1w)

2. **Technical Analysis** (`src/services/analysis.ts`)
   - `analyzeTechnicals()` - Calculates all indicators and identifies trend/strength
   - `calculateRSI()`, `calculateEMA()`, `calculateMACD()`, `calculateATR()`, `calculateBollingerBands()`
   - `findSupportResistance()` - Identifies key price levels using pivot points
   - `detectPatterns()` - Identifies chart patterns (triangles, engulfing patterns)

3. **Signal Generation** (`src/services/analysis.ts`)
   - `generateSignal()` - Combines analysis to create actionable signals
   - Minimum requirements: 65% strength, confluence, 1.5:1 risk/reward ratio
   - Signals include: entry zone, stop loss, TP1, TP2, confidence score, patterns

4. **Signal States**
   - `PENDING` - Signal generated, waiting for price to enter zone
   - `ACTIVE` - Price entered the entry zone
   - `TP1_HIT`, `TP2_HIT` - Take profit levels reached
   - `SL_HIT` - Stop loss hit
   - `CANCELLED`, `EXPIRED` - Manually or automatically closed

### Component Organization

Components follow a modular structure split into logical domains:

- **`src/components/chart/`** - Chart visualization components
  - `GoldChart.tsx` - Main TradingView Lightweight Charts wrapper
  - `TimeframeSelector.tsx` - Timeframe selection control

- **`src/components/layout/`** - Layout components
  - `Header.tsx` - Main navigation with live price ticker

- **`src/components/signals/`** - Signal display components
  - `SignalCard.tsx` - Individual signal card (supports compact and full modes)

- **`src/components/ui/`** - Reusable UI primitives
  - `StatsCard.tsx` - Metric display cards
  - `Toaster.tsx` - Toast notification system

### Color System & Theming

The application uses a **custom color palette** defined in `src/app/globals.css`:

**Primary Colors (Gold):**
- `primary-*` (50-900) - Primary brand color for highlights and CTAs (gold shades)

**Secondary Colors (Navy):**
- `secondary-*` (50-950) - Background and UI element colors (navy shades)

**Semantic Colors:**
- `profit` (#10b981) - Green for bullish/wins
- `loss` (#ef4444) - Red for bearish/losses
- `pending` (#f59e0b) - Orange for pending states

**Legacy Color Names:**
For backward compatibility, `gold-*` and `navy-*` are still defined but **prefer using `primary-*` and `secondary-*`** for new code.

**IMPORTANT**: When using Tailwind classes, use the color names defined in the CSS variables (e.g., `text-primary-400`, `bg-secondary-950`, `text-profit`, `text-loss`). Do NOT hardcode hex values or use generic color names.

### API Integration

The app supports two modes:

1. **Live Data** - When `NEXT_PUBLIC_MARKET_API_KEY` is set in `.env.local`
   - Provider: Finnhub (60 calls/minute free tier)
   - Alternative: Twelve Data (800 calls/day free tier)

2. **Simulated Data** - When no API key is configured
   - Realistic price movements using mathematical models
   - Good for development and testing

### Price Streaming

`PriceStream` class (`src/services/market.ts`) provides real-time price updates:
- Polls API every 5 seconds
- Uses subscription pattern for multiple consumers
- Automatically starts/stops based on subscribers

## Important Patterns & Conventions

### Signal Status Management
- Signals are immutable once created (use `updateSignal` to modify)
- Status transitions must follow the valid flow: PENDING → ACTIVE → (TP1_HIT | TP2_HIT | SL_HIT)
- PnL is calculated in pips and stored in `pnlPips` field

### Risk Management Defaults
Located in `src/store/index.ts`:
```typescript
riskManagement: {
  maxRiskPercent: 2,      // Max 2% risk per trade
  minRiskReward: 1.5,     // Minimum 1.5:1 R:R
}
```

### Browser Notifications
- Requires user permission (requested via `useNotificationPermission` hook)
- Notifications automatically trigger when new signals are added to the store
- Icon path: `/logo.png`

## File Structure Notes

- **No `tailwind.config.ts`** - Configuration is in `@theme` directive in `globals.css` (Tailwind v4 approach)
- **Font loading** - Custom fonts loaded in `src/app/layout.tsx` using Next.js Font optimization
- **Type definitions** - All TypeScript types centralized in `src/types/index.ts`

## Common Development Scenarios

### Adding a New Indicator
1. Create calculation function in `src/services/analysis.ts`
2. Add to `IndicatorValues` type in `src/types/index.ts`
3. Include in `analyzeTechnicals()` function
4. Optionally use in `generateSignal()` for signal quality

### Adding a New Signal Status
1. Add to `SignalStatus` type in `src/types/index.ts`
2. Update status labels in `SignalCard.tsx`
3. Add status-specific styling classes
4. Update status filtering in store methods (`getActiveSignals`, `getClosedSignals`)

### Customizing Chart Appearance
Chart colors are hardcoded in `GoldChart.tsx` to match the design system:
- Background: transparent
- Grid lines: `rgba(50, 70, 100, 0.2)`
- Crosshair: `#fbbf24` (gold-400)
- Candles: `#10b981` (profit) / `#ef4444` (loss)

## Environment Variables

```env
# Optional - Falls back to simulated data if not provided
NEXT_PUBLIC_MARKET_API_KEY=your_api_key_here
NEXT_PUBLIC_MARKET_API_PROVIDER=finnhub  # or "twelvedata"
```

## Styling Guidelines

- Use Tailwind utility classes for all styling
- Glass morphism effect: `glass-card` class (defined in globals.css)
- Animations: Use CSS variables from `globals.css` (e.g., `animate-fade-in`, `animate-slide-up`)
- Responsive: Mobile-first approach with `sm:`, `md:`, `lg:` breakpoints
- Dark mode: Application is dark-mode only (no light mode toggle)
