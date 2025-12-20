import { ChevronDown } from 'lucide-react';
import { TIMEFRAMES } from '@/lib/constants';

interface TimeframeSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className='space-y-3'>
      <label className='block text-sm font-semibold text-amber-300'>
        Timeframe
      </label>
      <div className='relative'>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className='w-full px-4 py-3 bg-white/10 border-2 border-amber-400/50 rounded-xl text-white font-medium focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent appearance-none cursor-pointer hover:bg-white/20 transition-all'>
          {TIMEFRAMES.map((tf) => (
            <option
              key={tf.value}
              value={tf.value}
              className='bg-slate-800 text-white'>
              {tf.label}
            </option>
          ))}
        </select>
        <ChevronDown className='absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-400 pointer-events-none' />
      </div>
    </div>
  );
}
