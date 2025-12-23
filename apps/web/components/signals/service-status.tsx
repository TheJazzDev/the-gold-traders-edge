'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock, TrendingUp } from 'lucide-react';

interface ServiceStatusData {
  status: string;
  candles_processed: number;
  signals_generated: number;
  signal_rate: number | null;
  last_candle_time: string | null;
  next_candle_time: string | null;
  current_price: number | null;
  datafeed_type: string;
  symbol: string;
  timeframe: string;
}

export function ServiceStatus() {
  const [status, setStatus] = useState<ServiceStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/v1/signals/latest');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      // Transform the latest endpoint data to status format
      const transformedStatus: ServiceStatusData = {
        status: 'running', // Assume running if we get a response
        candles_processed: 0, // Not available from this endpoint
        signals_generated: data.signals?.length || 0,
        signal_rate: null,
        last_candle_time: data.timestamp,
        next_candle_time: null, // Calculate based on timeframe
        current_price: data.current_price,
        datafeed_type: 'yahoo',
        symbol: data.symbol || 'XAUUSD',
        timeframe: data.timeframe || '4H'
      };
      setStatus(transformedStatus);
      setError(null);
    } catch (err) {
      setError('Unable to connect to signal service');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Update every 30 seconds
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

  if (error || !status) {
    return (
      <div className='bg-linear-to-br from-red-500/20 to-red-500/10 backdrop-blur-xl rounded-2xl border border-red-500/30 p-6 shadow-2xl'>
        <div className='flex items-center gap-3'>
          <div className='w-3 h-3 bg-red-500 rounded-full animate-pulse'></div>
          <div>
            <h3 className='text-lg font-bold text-red-300'>Service Offline</h3>
            <p className='text-sm text-white/60 mt-1'>
              {error || 'Unable to connect to signal generation service'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isRunning = status.status === 'running';
  const timeUntilNextCandle = status.next_candle_time
    ? new Date(status.next_candle_time).getTime() - Date.now()
    : null;

  const formatTimeRemaining = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl'>
      <div className='flex items-center justify-between mb-6'>
        <h2 className='text-xl font-bold text-white flex items-center gap-2'>
          <Activity className='w-6 h-6 text-green-400' />
          Signal Service Status
        </h2>
        <div className='flex items-center gap-2'>
          <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
          <span className={`text-sm font-semibold ${isRunning ? 'text-green-400' : 'text-red-400'}`}>
            {isRunning ? 'Active' : 'Stopped'}
          </span>
        </div>
      </div>

      <div className='grid sm:grid-cols-2 lg:grid-cols-3 gap-4'>
        {/* Current Price */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <TrendingUp className='w-4 h-4 text-amber-400' />
            <span className='text-sm text-white/60'>Current Price</span>
          </div>
          <div className='text-2xl font-bold text-white'>
            {status.current_price ? `$${status.current_price.toFixed(2)}` : 'N/A'}
          </div>
          <div className='text-xs text-white/40 mt-1'>{status.symbol}</div>
        </div>

        {/* Signals Generated */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <span className='text-sm text-white/60'>Signals Generated</span>
          </div>
          <div className='text-2xl font-bold text-white'>{status.signals_generated}</div>
          <div className='text-xs text-white/40 mt-1'>
            {status.signal_rate ? `${status.signal_rate.toFixed(1)}% signal rate` : 'Calculating...'}
          </div>
        </div>

        {/* Next Candle */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <Clock className='w-4 h-4 text-blue-400' />
            <span className='text-sm text-white/60'>Next Candle</span>
          </div>
          <div className='text-2xl font-bold text-white'>
            {timeUntilNextCandle && timeUntilNextCandle > 0
              ? formatTimeRemaining(timeUntilNextCandle)
              : 'Processing...'}
          </div>
          <div className='text-xs text-white/40 mt-1'>{status.timeframe} timeframe</div>
        </div>
      </div>

      {/* Waiting for Signal Indicator */}
      {isRunning && status.signals_generated === 0 && (
        <div className='mt-4 bg-blue-500/20 border border-blue-500/30 rounded-xl p-4'>
          <div className='flex items-center gap-3'>
            <div className='flex gap-1'>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '0ms' }}></div>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '150ms' }}></div>
              <div className='w-2 h-2 bg-blue-400 rounded-full animate-bounce' style={{ animationDelay: '300ms' }}></div>
            </div>
            <div className='text-sm text-blue-300 font-medium'>
              Waiting for first signal... Service is monitoring the market.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
