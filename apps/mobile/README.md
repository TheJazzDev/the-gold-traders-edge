# Gold Signal Mobile App

React Native mobile application for The Gold Trader's Edge platform.

## Features (Planned)

- [ ] User authentication (login/register)
- [ ] Real-time signal notifications
- [ ] Signal dashboard with charts
- [ ] Trade history & performance stats
- [ ] MT5 account connection
- [ ] One-tap trade execution
- [ ] Push notification settings
- [ ] Subscription management

## Tech Stack

- **Framework**: React Native 0.73+
- **Navigation**: React Navigation
- **State**: Zustand / Redux Toolkit
- **Styling**: NativeWind (Tailwind CSS)
- **Charts**: Victory Native / react-native-charts-wrapper
- **Push**: Firebase Cloud Messaging
- **Auth**: Firebase Auth / Custom JWT

## Screens (Planned)

```
├── Auth
│   ├── Login
│   ├── Register
│   └── ForgotPassword
├── Main
│   ├── Dashboard (signal list)
│   ├── SignalDetail
│   ├── History
│   └── Performance
├── Settings
│   ├── Profile
│   ├── MT5Connection
│   ├── Notifications
│   └── Subscription
```

## Development

### Prerequisites
- Node.js 18+
- React Native CLI
- Xcode (for iOS)
- Android Studio (for Android)

### Setup

```bash
cd apps/mobile
npm install

# iOS
cd ios && pod install && cd ..
npm run ios

# Android
npm run android
```

### Environment Variables

Create `.env` file:
```env
API_URL=http://localhost:8000
WS_URL=ws://localhost:8000/signals/live
FIREBASE_API_KEY=xxx
```

## Status: 🚧 Not Started

This app will be developed in Phase 3.
