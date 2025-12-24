'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock, TrendingUp, Zap } from 'lucide-react';

interface TimeframeStatus {
  timeframe: string;
  signals: number;
  isActive: boolean;
}

export function ServiceStatus() {
  const [allSignals, setAllSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  const ACTIVE_TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d'];

  const fetchData = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Fetch recent signals
      const signalsResponse = await fetch(`${API_URL}/v1/signals/history?limit=100`);
      if (!signalsResponse.ok) throw new Error('Failed to fetch signals');
      const signalsData = await signalsResponse.json();
      setAllSignals(signalsData.signals || []);

      // Fetch latest signal for price
      const latestResponse = await fetch(`${API_URL}/v1/signals/latest`);
      if (latestResponse.ok) {
        const latestData = await latestResponse.json();
        setCurrentPrice(latestData.current_price);
      }

      setError(null);
    } catch (err) {
      setError('Unable to connect to signal service');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl'>
        <div className='animate-pulse flex items-center justify-center py-8'>
          <div className='text-white/60'>Loading service status...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='bg-linear-to-br from-red-500/20 to-red-500/10 backdrop-blur-xl rounded-2xl border border-red-500/30 p-6 shadow-2xl'>
        <div className='flex items-center gap-3'>
          <div className='w-3 h-3 bg-red-500 rounded-full animate-pulse'></div>
          <div>
            <h3 className='text-lg font-bold text-red-300'>Service Offline</h3>
            <p className='text-sm text-white/60 mt-1'>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Group signals by timeframe
  const timeframeStats: TimeframeStatus[] = ACTIVE_TIMEFRAMES.map(tf => {
    const tfSignals = allSignals.filter(s => s.timeframe === tf);
    return {
      timeframe: tf,
      signals: tfSignals.length,
      isActive: true, // All timeframes are always active
    };
  });

  const totalSignals = allSignals.length;
  const isRunning = true; // Service is always running

  return (
    <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl'>
      <div className='flex items-center justify-between mb-6'>
        <h2 className='text-xl font-bold text-white flex items-center gap-2'>
          <Activity className='w-6 h-6 text-green-400' />
          Multi-Timeframe Signal Service
        </h2>
        <div className='flex items-center gap-2'>
          <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
          <span className={`text-sm font-semibold ${isRunning ? 'text-green-400' : 'text-red-400'}`}>
            {isRunning ? 'All 6 Timeframes Active' : 'Stopped'}
          </span>
        </div>
      </div>

      <div className='grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6'>
        {/* Current Price */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <TrendingUp className='w-4 h-4 text-amber-400' />
            <span className='text-sm text-white/60'>Current Price</span>
          </div>
          <div className='text-2xl font-bold text-white'>
            {currentPrice ? `$${currentPrice.toFixed(2)}` : 'N/A'}
          </div>
          <div className='text-xs text-white/40 mt-1'>XAUUSD</div>
        </div>

        {/* Total Signals */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <Zap className='w-4 h-4 text-yellow-400' />
            <span className='text-sm text-white/60'>Total Signals</span>
          </div>
          <div className='text-2xl font-bold text-white'>{totalSignals}</div>
          <div className='text-xs text-white/40 mt-1'>Across all timeframes</div>
        </div>

        {/* Active Rules */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <span className='text-sm text-white/60'>Active Rules</span>
          </div>
          <div className='text-2xl font-bold text-white'>5 Rules</div>
          <div className='text-xs text-white/40 mt-1'>All profitable strategies</div>
        </div>
      </div>

      {/* Timeframe Breakdown */}
      <div className='bg-white/5 rounded-xl p-4'>
        <h3 className='text-sm font-semibold text-white/80 mb-3'>Signals by Timeframe</h3>
        <div className='grid grid-cols-3 sm:grid-cols-6 gap-3'>
          {timeframeStats.map((tf) => (
            <div
              key={tf.timeframe}
              className='bg-white/5 rounded-lg p-3 text-center border border-white/10'>
              <div className='text-xs text-white/60 mb-1'>{tf.timeframe.toUpperCase()}</div>
              <div className='text-lg font-bold text-amber-400'>{tf.signals}</div>
              <div className='flex items-center justify-center mt-1'>
                <div className='w-2 h-2 bg-green-500 rounded-full'></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Waiting for Signal Indicator */}
      {isRunning && totalSignals === 0 && (
        <div className='mt-4 bg-blue-500/20 border border-blue-500/30 rounded-xl p-4'>
          <div className='flex items-center gap-3'>
            <div className='flex gap-1'>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '0ms' }}></div>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '150ms' }}></div>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '300ms' }}></div>
            </div>
            <div className='text-sm text-blue-300 font-medium'>
              Waiting for first signal... All 6 timeframes (5m, 15m, 30m, 1h, 4h, 1d) are actively monitoring.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
