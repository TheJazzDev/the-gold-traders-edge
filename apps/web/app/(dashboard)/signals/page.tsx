'use client';

import { Header } from '@/components/dashboard/Header';
import { SignalsList } from '@/components/signals/SignalsList';

export default function SignalsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Trading Signals"
        description="Monitor and analyze all generated trading signals"
      />

      <div className="flex-1 p-4 sm:p-6 overflow-y-auto">
        <SignalsList />
      </div>
    </div>
  );
}
