# Admin Panel with Subscription Tiers - Architecture

## Subscription Model

### Free Tier (Signal Viewer)
**Price:** $0/month
**Features:**
- ✅ View recent signals (last 7 days)
- ✅ Basic signal details (entry, SL, TP)
- ✅ Signal history (limited to 50 signals)
- ❌ No auto-trading
- ❌ No real-time alerts
- ❌ No advanced analytics
- ❌ No settings control

**Use Case:** Users who want to see your signals and manually trade them

---

### Pro Tier (Auto-Trader)
**Price:** $49/month
**Features:**
- ✅ Everything in Free
- ✅ **Auto-trading** (connect your own MT5/MetaAPI account)
- ✅ Real-time signal alerts (Telegram, Email)
- ✅ Full signal history (unlimited)
- ✅ Live trade monitoring
- ✅ **Basic settings control:**
  - Risk per trade (0.5% - 2%)
  - Max positions (1-5)
  - Enable/disable strategies
- ✅ Performance analytics
- ✅ Trade journal
- ❌ No multi-account management
- ❌ No custom strategies
- ❌ No API access

**Use Case:** Traders who want to auto-trade your signals with basic customization

---

### Premium Tier (Full Control)
**Price:** $149/month
**Features:**
- ✅ Everything in Pro
- ✅ **Full admin access** (all settings)
- ✅ **Advanced risk management:**
  - Risk per trade (0.1% - 10%)
  - Max positions (1-20)
  - Custom daily/weekly loss limits
  - Multi-timeframe selection
- ✅ **Multi-account management** (trade multiple accounts)
- ✅ **Custom strategy parameters**
- ✅ **API access** for custom integrations
- ✅ **Priority support**
- ✅ **Webhook notifications**
- ✅ **Advanced analytics:**
  - Drawdown analysis
  - Risk metrics
  - Sharpe ratio
  - Custom date ranges

**Use Case:** Professional traders, fund managers, or users who want full control

---

## Feature Access Matrix

| Feature | Free | Pro | Premium |
|---------|------|-----|---------|
| **Signals** | | | |
| View signals (7 days) | ✅ | ✅ | ✅ |
| Full signal history | ❌ | ✅ | ✅ |
| Real-time notifications | ❌ | ✅ | ✅ |
| Signal filtering | ❌ | ✅ | ✅ |
| **Trading** | | | |
| Manual trading | ✅ | ✅ | ✅ |
| Auto-trading | ❌ | ✅ | ✅ |
| Multi-account | ❌ | ❌ | ✅ |
| Copy trading | ❌ | ❌ | ✅ |
| **Settings** | | | |
| View settings | ✅ | ✅ | ✅ |
| Basic risk settings | ❌ | ✅ (limited) | ✅ (full) |
| Strategy selection | ❌ | ✅ (presets) | ✅ (custom) |
| Timeframe selection | ❌ | ❌ | ✅ |
| **Analytics** | | | |
| Basic stats | ✅ | ✅ | ✅ |
| Performance charts | ❌ | ✅ | ✅ |
| Advanced metrics | ❌ | ❌ | ✅ |
| Custom date ranges | ❌ | ❌ | ✅ |
| **Notifications** | | | |
| Email alerts | ❌ | ✅ | ✅ |
| Telegram bot | ❌ | ✅ | ✅ |
| Webhooks | ❌ | ❌ | ✅ |
| SMS alerts | ❌ | ❌ | ✅ (addon) |
| **Support** | | | |
| Community support | ✅ | ✅ | ✅ |
| Email support | ❌ | ✅ | ✅ |
| Priority support | ❌ | ❌ | ✅ |
| **API Access** | | | |
| Read-only API | ❌ | ❌ | ✅ |
| Full API access | ❌ | ❌ | ✅ |

---

## Database Schema for Subscriptions

```typescript
// Subscription tiers
enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  PREMIUM = 'premium'
}

// User model
interface User {
  id: string;
  email: string;
  name: string;
  subscription_tier: SubscriptionTier;
  subscription_status: 'active' | 'cancelled' | 'past_due' | 'trialing';
  subscription_start_date: Date;
  subscription_end_date: Date;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;

  // MetaAPI connection (Pro/Premium only)
  metaapi_account_id?: string;
  metaapi_connected: boolean;

  // Settings (tier-dependent)
  settings: UserSettings;

  // Usage tracking
  signals_viewed_this_month: number;
  api_calls_this_month: number;

  created_at: Date;
  updated_at: Date;
}

// User settings (what they can control based on tier)
interface UserSettings {
  // Risk management (Pro: limited, Premium: full)
  max_risk_per_trade: number;  // Pro: 0.5-2%, Premium: 0.1-10%
  max_positions: number;         // Pro: 1-5, Premium: 1-20
  max_daily_loss: number;        // Premium only
  max_weekly_loss: number;       // Premium only

  // Strategies (Pro: presets, Premium: custom)
  enabled_strategies: string[];  // Pro: all or none, Premium: individual

  // Timeframes (Premium only)
  enabled_timeframes: string[];  // Premium: custom, Others: all

  // Notifications (Pro+)
  telegram_enabled: boolean;
  telegram_chat_id?: string;
  email_notifications: boolean;
  webhook_url?: string;          // Premium only

  // Trading (Pro+)
  auto_trading_enabled: boolean;
  dry_run_mode: boolean;
}

// Feature access control
interface FeatureAccess {
  tier: SubscriptionTier;
  features: {
    signals: {
      view_history_days: number;    // Free: 7, Pro/Premium: unlimited
      real_time_alerts: boolean;     // Free: false, Pro+: true
    };
    trading: {
      auto_trading: boolean;         // Free: false, Pro+: true
      multi_account: boolean;        // Free/Pro: false, Premium: true
    };
    settings: {
      risk_range: [number, number];  // Free: none, Pro: [0.5, 2], Premium: [0.1, 10]
      max_positions_range: [number, number]; // Pro: [1, 5], Premium: [1, 20]
      strategy_control: 'none' | 'preset' | 'custom'; // Free: none, Pro: preset, Premium: custom
      timeframe_control: boolean;    // Free/Pro: false, Premium: true
    };
    analytics: {
      basic_stats: boolean;          // All: true
      advanced_metrics: boolean;     // Free/Pro: false, Premium: true
      custom_date_ranges: boolean;   // Free/Pro: false, Premium: true
    };
    api: {
      enabled: boolean;              // Free/Pro: false, Premium: true
      rate_limit: number;            // Premium: 1000 req/hour
    };
  };
}
```

---

## App Structure with Subscription Gates

```
apps/web/
├── app/
│   ├── (public)/              # No auth required
│   │   ├── page.tsx           # Landing page
│   │   ├── pricing/
│   │   │   └── page.tsx       # Pricing page
│   │   └── login/
│   │       └── page.tsx       # Login/signup
│   │
│   ├── (dashboard)/           # Auth required
│   │   ├── layout.tsx         # Dashboard shell with sidebar
│   │   ├── page.tsx           # Dashboard home
│   │   │
│   │   ├── signals/           # FREE+ (All tiers)
│   │   │   ├── page.tsx       # Signal list
│   │   │   └── [id]/
│   │   │       └── page.tsx   # Signal details
│   │   │
│   │   ├── trades/            # PRO+ (Auto-trading required)
│   │   │   ├── page.tsx       # Trade history
│   │   │   ├── active/
│   │   │   │   └── page.tsx   # Active positions
│   │   │   └── [id]/
│   │   │       └── page.tsx   # Trade details
│   │   │
│   │   ├── settings/          # PRO+ (Limited for Pro, Full for Premium)
│   │   │   ├── page.tsx       # Settings dashboard
│   │   │   ├── risk/
│   │   │   │   └── page.tsx   # Risk management settings
│   │   │   ├── strategies/
│   │   │   │   └── page.tsx   # Strategy selection
│   │   │   ├── notifications/
│   │   │   │   └── page.tsx   # Alert settings
│   │   │   └── account/
│   │   │       └── page.tsx   # MetaAPI connection
│   │   │
│   │   ├── analytics/         # PRO+ (Basic for Pro, Advanced for Premium)
│   │   │   ├── page.tsx       # Analytics dashboard
│   │   │   ├── performance/
│   │   │   │   └── page.tsx   # Performance metrics
│   │   │   └── reports/
│   │   │       └── page.tsx   # PREMIUM ONLY: Custom reports
│   │   │
│   │   ├── api-keys/          # PREMIUM ONLY
│   │   │   └── page.tsx       # API key management
│   │   │
│   │   └── subscription/
│   │       ├── page.tsx       # Current plan
│   │       └── upgrade/
│   │           └── page.tsx   # Upgrade options
│   │
│   └── api/                   # API routes
│       ├── auth/
│       ├── webhooks/
│       └── proxy/             # Proxy to Railway API
│
├── components/
│   ├── subscription/
│   │   ├── SubscriptionGate.tsx     # Component to gate features
│   │   ├── UpgradePrompt.tsx        # CTA to upgrade
│   │   └── PricingCard.tsx
│   │
│   ├── dashboard/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── StatsCard.tsx
│   │
│   ├── signals/
│   │   ├── SignalsList.tsx
│   │   ├── SignalCard.tsx
│   │   └── SignalFilters.tsx
│   │
│   ├── settings/
│   │   ├── RiskManagementPanel.tsx
│   │   ├── StrategySelector.tsx
│   │   └── NotificationSettings.tsx
│   │
│   └── ui/                    # shadcn components
│
├── lib/
│   ├── subscription/
│   │   ├── check-access.ts    # Check if user has access to feature
│   │   ├── tiers.ts           # Tier definitions
│   │   └── limits.ts          # Usage limits
│   │
│   ├── api/
│   │   ├── client.ts          # API client with auth
│   │   └── endpoints.ts       # API endpoints
│   │
│   └── auth/
│       └── session.ts
│
└── hooks/
    ├── useSubscription.ts     # Get user's subscription
    ├── useFeatureAccess.ts    # Check feature access
    └── useUsageLimit.ts       # Track usage limits
```

---

## Subscription Gate Component

```typescript
// components/subscription/SubscriptionGate.tsx
'use client';

import { useSubscription } from '@/hooks/useSubscription';
import { UpgradePrompt } from './UpgradePrompt';

interface SubscriptionGateProps {
  children: React.ReactNode;
  requiredTier: 'pro' | 'premium';
  feature: string;
  fallback?: React.ReactNode;
}

export function SubscriptionGate({
  children,
  requiredTier,
  feature,
  fallback
}: SubscriptionGateProps) {
  const { tier, hasAccess } = useSubscription();

  if (!hasAccess(requiredTier)) {
    return fallback || (
      <UpgradePrompt
        currentTier={tier}
        requiredTier={requiredTier}
        feature={feature}
      />
    );
  }

  return <>{children}</>;
}

// Usage example
function AdvancedAnalytics() {
  return (
    <SubscriptionGate requiredTier="premium" feature="Advanced Analytics">
      {/* Premium-only content */}
      <DrawdownChart />
      <SharpeRatioMetrics />
      <CustomDateRangeSelector />
    </SubscriptionGate>
  );
}
```

---

## Settings Panel with Tier-Based Limits

```typescript
// components/settings/RiskManagementPanel.tsx
'use client';

import { useSubscription } from '@/hooks/useSubscription';
import { Slider } from '@/components/ui/slider';

export function RiskManagementPanel() {
  const { tier, limits } = useSubscription();
  const [maxRisk, setMaxRisk] = useState(1.0);

  // Get limits based on tier
  const riskLimits = limits.risk_range; // [0.5, 2] for Pro, [0.1, 10] for Premium

  return (
    <div className="space-y-6">
      <div>
        <label>Max Risk Per Trade</label>
        <Slider
          value={[maxRisk]}
          min={riskLimits[0]}
          max={riskLimits[1]}
          step={0.1}
          onValueChange={([value]) => setMaxRisk(value)}
        />
        <p className="text-sm text-muted-foreground">
          Current: {maxRisk}% (Tier: {tier})
        </p>

        {tier === 'pro' && (
          <p className="text-xs text-yellow-600">
            💎 Upgrade to Premium to set risk up to 10%
          </p>
        )}
      </div>
    </div>
  );
}
```

---

## Usage Tracking

```typescript
// lib/subscription/usage-tracker.ts
export async function trackUsage(userId: string, action: string) {
  // Increment usage counter
  await db.user.update({
    where: { id: userId },
    data: {
      signals_viewed_this_month: {
        increment: 1
      }
    }
  });

  // Check if limit exceeded
  const user = await db.user.findUnique({ where: { id: userId } });
  const limit = getTierLimits(user.subscription_tier);

  if (user.signals_viewed_this_month > limit.signals_per_month) {
    throw new Error('Monthly signal limit exceeded. Please upgrade.');
  }
}
```

---

## Stripe Integration (Payments)

```typescript
// lib/stripe/checkout.ts
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function createCheckoutSession(
  userId: string,
  tier: 'pro' | 'premium'
) {
  const prices = {
    pro: process.env.STRIPE_PRO_PRICE_ID,
    premium: process.env.STRIPE_PREMIUM_PRICE_ID
  };

  const session = await stripe.checkout.sessions.create({
    customer_email: user.email,
    line_items: [
      {
        price: prices[tier],
        quantity: 1,
      },
    ],
    mode: 'subscription',
    success_url: `${process.env.NEXT_PUBLIC_URL}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/pricing`,
    metadata: {
      userId,
      tier
    }
  });

  return session.url;
}
```

---

## Next Steps

1. ✅ Install additional dependencies:
   ```bash
   cd apps/web
   npm install @tanstack/react-query zustand stripe @stripe/stripe-js
   npm install -D @types/stripe
   ```

2. ✅ Set up authentication (NextAuth or Clerk)

3. ✅ Create subscription gates and tier checks

4. ✅ Build settings panel with tier-based limits

5. ✅ Integrate Stripe for payments

6. ✅ Add usage tracking

Ready to start building?
