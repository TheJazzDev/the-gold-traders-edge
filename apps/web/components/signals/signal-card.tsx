'use client';

import { TrendingUp, TrendingDown, Target, Shield, Award } from 'lucide-react';

interface SignalCardProps {
  signal: {
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
  };
}

export function SignalCard({ signal }: SignalCardProps) {
  const isLong = signal.direction === 'LONG';
  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300',
    active: 'bg-blue-500/20 border-blue-500/30 text-blue-300',
    closed_tp: 'bg-green-500/20 border-green-500/30 text-green-300',
    closed_sl: 'bg-red-500/20 border-red-500/30 text-red-300',
    closed_manual: 'bg-gray-500/20 border-gray-500/30 text-gray-300',
  };

  return (
    <div className={`bg-linear-to-br ${isLong ? 'from-green-500/20 to-green-500/10' : 'from-red-500/20 to-red-500/10'} backdrop-blur-xl rounded-2xl border ${isLong ? 'border-green-500/30' : 'border-red-500/30'} p-6 shadow-2xl hover:scale-[1.02] transition-transform`}>
      {/* Header */}
      <div className='flex items-center justify-between mb-4'>
        <div className='flex items-center gap-3'>
          {isLong ? (
            <TrendingUp className='w-8 h-8 text-green-400' />
          ) : (
            <TrendingDown className='w-8 h-8 text-red-400' />
          )}
          <div>
            <h3 className={`text-2xl font-bold ${isLong ? 'text-green-300' : 'text-red-300'}`}>
              {signal.direction}
            </h3>
            <p className='text-sm text-white/60'>{signal.strategy_name}</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold border ${statusColors[signal.status] || statusColors.pending}`}>
          {signal.status.replace('_', ' ').toUpperCase()}
        </div>
      </div>

      {/* Symbol & Time */}
      <div className='flex items-center justify-between mb-4 pb-4 border-b border-white/10'>
        <div>
          <div className='text-sm text-white/60'>Symbol</div>
          <div className='text-xl font-bold text-white'>{signal.symbol}</div>
        </div>
        <div className='text-right'>
          <div className='text-sm text-white/60'>Timeframe</div>
          <div className='text-xl font-bold text-white'>{signal.timeframe}</div>
        </div>
        <div className='text-right'>
          <div className='text-sm text-white/60'>Time</div>
          <div className='text-sm font-medium text-white'>
            {new Date(signal.timestamp).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Price Levels */}
      <div className='grid grid-cols-3 gap-4 mb-4'>
        <div className='bg-white/5 rounded-xl p-3'>
          <div className='flex items-center gap-2 mb-1'>
            <Target className='w-4 h-4 text-blue-400' />
            <span className='text-xs text-white/60'>Entry</span>
          </div>
          <div className='text-lg font-bold text-white'>${signal.entry_price.toFixed(2)}</div>
        </div>
        <div className='bg-white/5 rounded-xl p-3'>
          <div className='flex items-center gap-2 mb-1'>
            <Shield className='w-4 h-4 text-red-400' />
            <span className='text-xs text-white/60'>Stop Loss</span>
          </div>
          <div className='text-lg font-bold text-white'>${signal.stop_loss.toFixed(2)}</div>
        </div>
        <div className='bg-white/5 rounded-xl p-3'>
          <div className='flex items-center gap-2 mb-1'>
            <Award className='w-4 h-4 text-green-400' />
            <span className='text-xs text-white/60'>Take Profit</span>
          </div>
          <div className='text-lg font-bold text-white'>${signal.take_profit.toFixed(2)}</div>
        </div>
      </div>

      {/* Risk Metrics */}
      <div className='grid grid-cols-2 gap-4'>
        <div className='bg-white/5 rounded-xl p-3'>
          <div className='text-xs text-white/60 mb-1'>Risk:Reward Ratio</div>
          <div className='text-xl font-bold text-amber-400'>
            1:{signal.risk_reward_ratio.toFixed(2)}
          </div>
          <div className='text-xs text-white/40 mt-1'>
            Risk: {signal.risk_pips.toFixed(0)} pips | Reward: {signal.reward_pips.toFixed(0)} pips
          </div>
        </div>
        <div className='bg-white/5 rounded-xl p-3'>
          <div className='text-xs text-white/60 mb-1'>Confidence</div>
          <div className='flex items-center gap-2'>
            <div className='flex-1 bg-white/10 rounded-full h-2 overflow-hidden'>
              <div
                className='bg-linear-to-r from-amber-500 to-yellow-500 h-full rounded-full'
                style={{ width: `${signal.confidence * 100}%` }}
              ></div>
            </div>
            <span className='text-sm font-bold text-white'>{(signal.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
