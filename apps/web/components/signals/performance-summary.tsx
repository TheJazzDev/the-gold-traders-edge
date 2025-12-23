'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, Target, Award, DollarSign } from 'lucide-react';

interface PerformanceData {
  total_signals: number;
  total_closed: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  largest_win: number;
  largest_loss: number;
}

export function PerformanceSummary() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPerformance = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/v1/analytics/summary`);
      if (!response.ok) throw new Error('Failed to fetch performance');
      const perfData = await response.json();

      // Transform API response to match our interface
      const transformed: PerformanceData = {
        total_signals: perfData.total_signals || 0,
        total_closed: (perfData.winning_signals || 0) + (perfData.losing_signals || 0),
        win_count: perfData.winning_signals || 0,
        loss_count: perfData.losing_signals || 0,
        win_rate: perfData.win_rate || 0,
        total_pnl: 0, // Not available in this endpoint
        total_pnl_pct: perfData.total_return_pct || 0,
        avg_win: perfData.avg_win || 0,
        avg_loss: perfData.avg_loss || 0,
        profit_factor: perfData.profit_factor || 0,
        largest_win: 0, // Not available in this endpoint
        largest_loss: 0, // Not available in this endpoint
      };

      setData(transformed);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformance();
    const interval = setInterval(fetchPerformance, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (loading || !data || data.total_signals === 0) {
    return null; // Don't show if no data
  }

  return (
    <div className='bg-linear-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 p-6 shadow-2xl mb-8'>
      <h2 className='text-xl font-bold text-white mb-6 flex items-center gap-2'>
        <Award className='w-6 h-6 text-amber-400' />
        Performance Summary
      </h2>

      <div className='grid sm:grid-cols-2 lg:grid-cols-4 gap-4'>
        {/* Total Signals */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <Target className='w-4 h-4 text-blue-400' />
            <span className='text-sm text-white/60'>Total Signals</span>
          </div>
          <div className='text-2xl font-bold text-white'>{data.total_signals}</div>
          <div className='text-xs text-white/40 mt-1'>
            {data.total_closed} closed
          </div>
        </div>

        {/* Win Rate */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <TrendingUp className='w-4 h-4 text-green-400' />
            <span className='text-sm text-white/60'>Win Rate</span>
          </div>
          <div className='text-2xl font-bold text-green-400'>
            {data.win_rate.toFixed(1)}%
          </div>
          <div className='text-xs text-white/40 mt-1'>
            {data.win_count}W / {data.loss_count}L
          </div>
        </div>

        {/* Profit Factor */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <Award className='w-4 h-4 text-amber-400' />
            <span className='text-sm text-white/60'>Profit Factor</span>
          </div>
          <div className='text-2xl font-bold text-amber-400'>
            {data.profit_factor.toFixed(2)}
          </div>
          <div className='text-xs text-white/40 mt-1'>
            Avg Win: ${data.avg_win.toFixed(0)} | Loss: ${Math.abs(data.avg_loss).toFixed(0)}
          </div>
        </div>

        {/* Total P&L */}
        <div className='bg-white/5 rounded-xl p-4'>
          <div className='flex items-center gap-2 mb-2'>
            <DollarSign className='w-4 h-4 text-purple-400' />
            <span className='text-sm text-white/60'>Total P&L</span>
          </div>
          <div className={`text-2xl font-bold ${data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${data.total_pnl.toFixed(2)}
          </div>
          <div className='text-xs text-white/40 mt-1'>
            {data.total_pnl_pct >= 0 ? '+' : ''}{data.total_pnl_pct.toFixed(2)}%
          </div>
        </div>
      </div>
    </div>
  );
}
