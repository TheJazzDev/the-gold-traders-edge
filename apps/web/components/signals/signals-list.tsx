'use client';

import { useEffect, useState } from 'react';
import { SignalCard } from './signal-card';
import { RefreshCw } from 'lucide-react';

interface Signal {
  id: number;
  timestamp: string;
  symbol: string;
  timeframe: string;
  strategy_name: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  status: string;
  risk_reward_ratio: number;
  risk_pips: number;
  reward_pips: number;
}

interface SignalsListProps {
  limit?: number;
}

export function SignalsList({ limit = 10 }: SignalsListProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = async () => {
    try {
      const response = await fetch(`http://localhost:8000/v1/signals/history?limit=${limit}`);
      if (!response.ok) throw new Error('Failed to fetch signals');
      const data = await response.json();
      // API returns array directly
      setSignals(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError('Unable to load signals');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [limit]);

  if (loading) {
    return (
      <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl'>
        <div className='animate-pulse flex items-center justify-center py-12'>
          <RefreshCw className='w-8 h-8 text-white/60 animate-spin' />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='bg-linear-to-br from-red-500/20 to-red-500/10 backdrop-blur-xl rounded-2xl border border-red-500/30 p-6 shadow-2xl'>
        <div className='text-center py-8'>
          <p className='text-red-300 font-semibold mb-2'>Failed to Load Signals</p>
          <p className='text-sm text-white/60'>{error}</p>
          <button
            onClick={fetchSignals}
            className='mt-4 px-4 py-2 bg-red-500/30 hover:bg-red-500/40 rounded-lg text-white text-sm transition-colors'
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (signals.length === 0) {
    return (
      <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-8 shadow-2xl'>
        <div className='text-center py-12'>
          <div className='text-6xl mb-4'>📊</div>
          <h3 className='text-xl font-bold text-white mb-2'>No Signals Yet</h3>
          <p className='text-white/60 text-sm max-w-md mx-auto'>
            The signal generation service is running but hasn't generated any signals yet.
            Signals will appear here as they are generated in real-time.
          </p>
          <div className='mt-6 flex justify-center gap-2'>
            <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '0ms' }}></div>
            <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '150ms' }}></div>
            <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '300ms' }}></div>
          </div>
          <p className='text-xs text-white/40 mt-2'>Monitoring market conditions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between mb-4'>
        <h2 className='text-2xl font-bold text-white'>Recent Signals</h2>
        <button
          onClick={fetchSignals}
          className='flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white text-sm transition-colors'
        >
          <RefreshCw className='w-4 h-4' />
          Refresh
        </button>
      </div>

      <div className='space-y-4'>
        {signals.map((signal) => (
          <SignalCard key={signal.id} signal={signal} />
        ))}
      </div>

      {signals.length >= limit && (
        <div className='text-center py-4'>
          <p className='text-sm text-white/60'>Showing latest {limit} signals</p>
        </div>
      )}
    </div>
  );
}
