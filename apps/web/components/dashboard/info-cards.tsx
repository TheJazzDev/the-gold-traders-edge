import { ALL_RULES, TIMEFRAMES } from '@/lib/constants';

interface InfoCardsProps {
  selectedRules: string[];
  timeframe: string;
  lastUpdate: Date | null;
  error: string | null;
}

export function InfoCards({
  selectedRules,
  timeframe,
  lastUpdate,
  error,
}: InfoCardsProps) {
  return (
    <div className='grid md:grid-cols-2 gap-4 sm:gap-6 mt-8'>
      {/* Trading Rules Guide */}
      <div className='bg-linear-to-br from-amber-500/20 to-yellow-500/10 backdrop-blur-xl rounded-2xl border border-amber-500/30 p-4 sm:p-6 shadow-xl'>
        <h3 className='text-base sm:text-lg font-bold text-amber-300 mb-3 sm:mb-4 flex items-center gap-2'>
          <span>🎯</span> Trading Rules Guide
        </h3>
        <ul className='space-y-2 sm:space-y-3 text-sm'>
          {ALL_RULES.map((rule) => (
            <li
              key={rule.id}
              className={`flex items-start gap-2 sm:gap-3 p-2 rounded-lg transition-all ${
                selectedRules.includes(rule.id)
                  ? 'bg-amber-500/20 border-l-4 border-amber-400'
                  : 'bg-white/5'
              }`}>
              <span
                className={`font-bold text-sm ${
                  selectedRules.includes(rule.id)
                    ? 'text-amber-400'
                    : 'text-white/40'
                }`}>
                #{rule.id}
              </span>
              <div>
                <span
                  className={
                    selectedRules.includes(rule.id)
                      ? 'text-white font-medium'
                      : 'text-white/60'
                  }>
                  {rule.name}
                </span>
                <p className='text-xs text-white/40 mt-0.5'>
                  {rule.performance}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* System Status */}
      <div className='bg-linear-to-br from-blue-500/20 to-purple-500/10 backdrop-blur-xl rounded-2xl border border-blue-500/30 p-4 sm:p-6 shadow-xl'>
        <h3 className='text-base sm:text-lg font-bold text-blue-300 mb-3 sm:mb-4 flex items-center gap-2'>
          <span>⚙️</span> System Status
        </h3>
        <div className='space-y-2 sm:space-y-3 text-sm'>
          <div className='flex items-center justify-between p-2 sm:p-3 bg-white/5 rounded-xl'>
            <span className='text-white/70 font-medium'>API Status</span>
            <span
              className={`px-2 sm:px-3 py-1 rounded-full text-xs font-bold ${
                error ? 'bg-red-500 text-white' : 'bg-green-500 text-white'
              }`}>
              {error ? '🔴 Offline' : '🟢 Online'}
            </span>
          </div>
          <div className='flex items-center justify-between p-2 sm:p-3 bg-white/5 rounded-xl'>
            <span className='text-white/70 font-medium'>
              Selected Timeframe
            </span>
            <span className='font-bold text-blue-300'>
              {TIMEFRAMES.find((t) => t.value === timeframe)?.label}
            </span>
          </div>
          <div className='flex items-center justify-between p-2 sm:p-3 bg-white/5 rounded-xl'>
            <span className='text-white/70 font-medium'>Active Rules</span>
            <span className='font-bold text-amber-300'>
              {selectedRules.length} of 6
            </span>
          </div>
          <div className='flex items-center justify-between p-2 sm:p-3 bg-white/5 rounded-xl'>
            <span className='text-white/70 font-medium'>Last Update</span>
            <span className='font-bold text-white'>
              {lastUpdate?.toLocaleTimeString() || 'Never'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
