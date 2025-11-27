# The Gold Trader's Edge

> **Mindset, Risk, and Smart Execution**

Professional XAUUSD trading signal application with real-time analysis, pattern detection, and smart notifications.

![The Gold Trader's Edge](./public/logo.png)

## Features

### Phase 1 (Current)
- 📊 **Real-time XAUUSD Chart** - Interactive candlestick charts with TradingView's Lightweight Charts
- 📈 **Technical Analysis Engine** - RSI, MACD, EMA, ATR, Bollinger Bands calculations
- 🎯 **Signal Detection** - Automated pattern recognition and signal generation
- 🔔 **Browser Notifications** - Real-time alerts when new signals are detected
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile

### Coming Soon
- 📧 Email notifications
- 🤖 Telegram bot integration
- 📊 Advanced analytics dashboard
- 🔙 Backtesting engine
- 🎨 Custom indicators

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **Charts**: Lightweight Charts (TradingView)
- **State**: Zustand
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone https://github.com/TheJazzDev/the-gold-traders-edge.git
cd the-gold-traders-edge
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env.local
```

4. Add your API key (optional - simulated data works without it):
```env
NEXT_PUBLIC_MARKET_API_KEY=your_finnhub_api_key
NEXT_PUBLIC_MARKET_API_PROVIDER=finnhub
```

Get a free API key from:
- [Finnhub](https://finnhub.io/) - 60 API calls/minute free
- [Twelve Data](https://twelvedata.com/) - 800 API calls/day free

5. Run the development server:
```bash
npm run dev
```

6. Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
src/
├── app/                  # Next.js App Router pages
│   ├── layout.tsx       # Root layout with fonts & theme
│   ├── page.tsx         # Main dashboard
│   └── globals.css      # Global styles & Tailwind
├── components/
│   ├── chart/           # Chart components
│   ├── layout/          # Header, Footer, etc.
│   ├── signals/         # Signal cards & lists
│   └── ui/              # Reusable UI components
├── hooks/               # Custom React hooks
├── lib/                 # Utility functions
├── services/            # API & business logic
│   ├── market.ts        # Price data fetching
│   └── analysis.ts      # Technical analysis
├── store/               # Zustand state management
└── types/               # TypeScript definitions
```

## Signal Generation Logic

The system generates signals based on multiple factors:

1. **Trend Analysis** - EMA crossovers and price position
2. **Momentum** - RSI divergence and overbought/oversold conditions
3. **Pattern Detection** - Triangles, engulfing patterns, etc.
4. **Support/Resistance** - Dynamic level detection
5. **Risk:Reward Filter** - Minimum 1.5:1 R:R required

Signals include:
- Entry zone (price range)
- Stop loss level
- Take profit targets (TP1, TP2)
- Confidence score (0-100%)
- Pattern identification

## Deployment

### Vercel (Recommended)

1. Push to GitHub
2. Import project in Vercel
3. Add environment variables
4. Deploy

```bash
npm run build
```

## Configuration

### Risk Management Settings

Edit `src/store/index.ts` to adjust default settings:

```typescript
riskManagement: {
  maxRiskPercent: 2,      // Max 2% risk per trade
  minRiskReward: 1.5,     // Minimum 1.5:1 R:R
}
```

### Notification Settings

Browser notifications require user permission. The app will prompt for permission when clicking "Enable Alerts".

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - feel free to use for personal or commercial projects.

## Disclaimer

This software is for educational and informational purposes only. It does not constitute financial advice. Trading involves substantial risk of loss. Past performance is not indicative of future results. Always conduct your own research and consult with a licensed financial advisor before making trading decisions.

---

Built with ❤️ by The Gold Trader's Edge Team
