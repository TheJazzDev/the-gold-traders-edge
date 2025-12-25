# Quick Start - Admin Panel

## ✅ What Was Just Built

A complete admin panel with subscription-based access control, integrated into your existing Next.js app.

## 🚀 How to Run (Local Development)

### 1. Start the Next.js dev server

```bash
cd apps/web
npm run dev
```

### 2. Access the admin panel

**Option 1: From the home page**
1. Open your browser to: **http://localhost:3000**
2. Click on "Admin Dashboard", "All Signals", or "Settings" buttons at the top

**Option 2: Direct URL**
- Open your browser to: **http://localhost:3000/dashboard**

## 📍 Routes You Can Access

| URL | Description |
|-----|-------------|
| `http://localhost:3000/dashboard` | Main dashboard |
| `http://localhost:3000/dashboard/signals` | All signals |
| `http://localhost:3000/dashboard/settings` | Settings (PRO+ feature) |

## 🎭 Testing Different Subscription Tiers

The subscription tier is stored in browser localStorage. To test different tiers:

### Method 1: Browser Console

```javascript
// Open browser DevTools (F12) and run:
localStorage.setItem('subscription-storage', JSON.stringify({
  state: { tier: 'premium', features: {} },
  version: 0
}));

// Then refresh the page
location.reload();
```

### Method 2: Change Code Temporarily

Edit `apps/web/lib/hooks/useSubscription.ts` line 24:

```typescript
// Change from:
tier: SubscriptionTier.FREE,

// To:
tier: SubscriptionTier.PREMIUM,  // or PRO
```

## 🔧 Environment Variables (Production)

When deploying, set these in Railway:

```bash
# Required
NEXT_PUBLIC_API_URL=https://the-gold-traders-edge-production.up.railway.app

# Optional (for auto-trading)
METAAPI_TOKEN=your_token
METAAPI_ACCOUNT_ID=your_account_id
ENABLE_AUTO_TRADING=true
DATA_FEED_TYPE=metaapi
```

## 📊 What Each Tier Can Do

### FREE Tier
- ✅ View dashboard
- ✅ View recent signals
- ❌ Cannot access settings
- ❌ No analytics

### PRO Tier ($49/month)
- ✅ Everything in FREE
- ✅ **Settings management** (limited ranges)
  - Risk: 0.5% - 2%
  - Positions: 1 - 5
- ✅ Strategy selection
- ✅ Auto-trading toggle

### PREMIUM Tier ($149/month)
- ✅ Everything in PRO
- ✅ **Full settings control**
  - Risk: 0.1% - 10%
  - Positions: 1 - 20
- ✅ Advanced analytics
- ✅ API access

## 🐛 Troubleshooting

### "Cannot find module '@/components/ui/...'"

Run:
```bash
npx shadcn@latest add button badge label input slider switch select
```

### "API calls failing"

1. Check `NEXT_PUBLIC_API_URL` is set
2. Verify backend is running
3. Check browser Network tab for errors

### "Settings not saving"

1. Run database migration first:
```bash
python packages/engine/src/database/init_settings_table.py
```

2. Verify settings table exists in PostgreSQL

### "Subscription gates not working"

1. Clear localStorage:
```javascript
localStorage.clear();
location.reload();
```

2. Set tier again using browser console method above

## 📱 Mobile Testing

The admin panel is fully responsive. Test on mobile by:

1. Open DevTools (F12)
2. Click device icon (Ctrl+Shift+M)
3. Select mobile device
4. All text and padding will adjust automatically

## 🎨 Customization

### Change Brand Colors

Edit `apps/web/app/globals.css` and modify CSS variables:

```css
:root {
  --primary: 38 92% 50%;  /* Amber - change these values */
}
```

### Modify Tier Pricing

Edit `apps/web/lib/subscription/tiers.ts`:

```typescript
export const TIER_PRICING = {
  [SubscriptionTier.PRO]: {
    monthly: 99,  // Change from 49 to 99
    ...
  }
}
```

### Add New Setting

1. Add to backend: `packages/engine/src/database/settings_models.py`
2. Add UI control in: `apps/web/app/(dashboard)/settings/page.tsx`
3. Use the `useUpdateSetting` hook to save changes

## ✨ What's Next?

### Immediate (Required for Production)

1. **Add authentication**
   - Install NextAuth or Clerk
   - Protect `/dashboard` routes
   - Add login/signup pages

2. **Run database migration**
   ```bash
   python packages/engine/src/database/init_settings_table.py
   ```

3. **Set environment variables** in Railway

### Future Enhancements (Optional)

1. **Stripe integration** for payments
2. **Real-time WebSocket** for live signals
3. **Email notifications** for signal alerts
4. **Advanced analytics** charts
5. **API key management** for PREMIUM users
6. **Trade history** with P&L tracking

## 📝 Summary

You now have:
- ✅ Complete admin dashboard at `/dashboard`
- ✅ Settings management UI
- ✅ Signal monitoring interface
- ✅ Subscription-based feature gating
- ✅ Mobile-responsive design
- ✅ Real-time data fetching with React Query

**Start the dev server and visit `/dashboard` to see it in action!** 🎉
