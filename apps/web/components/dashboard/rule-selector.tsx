import { ALL_RULES, PROFITABLE_RULES } from '@/lib/constants';

interface RuleSelectorProps {
  selectedRules: string[];
  onRuleToggle: (ruleId: string) => void;
  onSelectAll: () => void;
  onSelectProfitable: () => void;
  onClearAll: () => void;
}

export function RuleSelector({
  selectedRules,
  onRuleToggle,
  onSelectAll,
  onSelectProfitable,
  onClearAll,
}: RuleSelectorProps) {
  return (
    <div className='lg:col-span-2 space-y-3'>
      <div className='flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2'>
        <div>
          <label className='block text-sm font-semibold text-amber-300'>
            Trading Rules ({selectedRules.length} selected for backtest)
          </label>
          <p className='text-xs text-green-400 mt-1'>
            ✅ All 5 rules are ALWAYS active in live trading
          </p>
        </div>
        <div className='flex gap-2'>
          <button
            onClick={onSelectAll}
            className='text-xs px-2 sm:px-3 py-1 bg-amber-500/20 text-amber-300 rounded-full hover:bg-amber-500/30 transition-all border border-amber-500/30'>
            Select All
          </button>
          <button
            onClick={onClearAll}
            className='text-xs px-2 sm:px-3 py-1 bg-red-500/20 text-red-300 rounded-full hover:bg-red-500/30 transition-all border border-red-500/30'>
            Clear
          </button>
        </div>
      </div>

      <div className='grid sm:grid-cols-2 lg:grid-cols-3 gap-3'>
        {ALL_RULES.map((rule) => {
          const isSelected = selectedRules.includes(rule.id);

          return (
            <label
              key={rule.id}
              className={`relative flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                isSelected
                  ? 'bg-linear-to-br from-amber-500/30 to-yellow-500/20 border-2 border-amber-400 shadow-lg shadow-amber-500/20'
                  : 'bg-white/5 border-2 border-white/10 hover:border-white/30 hover:bg-white/10'
              }`}>
              <input
                type='checkbox'
                checked={isSelected}
                onChange={() => onRuleToggle(rule.id)}
                className='sr-only'
              />
              <div
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 mt-0.5 transition-all ${
                  isSelected
                    ? 'bg-amber-500 border-amber-500'
                    : 'border-white/40 bg-transparent'
                }`}>
                {isSelected && (
                  <svg
                    className='w-3 h-3 text-white'
                    fill='none'
                    viewBox='0 0 24 24'
                    stroke='currentColor'
                    strokeWidth={3}>
                    <path
                      strokeLinecap='round'
                      strokeLinejoin='round'
                      d='M5 13l4 4L19 7'
                    />
                  </svg>
                )}
              </div>
              <div className='flex-1 min-w-0'>
                <div className='flex items-center gap-2 flex-wrap'>
                  <span
                    className={`text-sm font-semibold ${
                      isSelected ? 'text-amber-300' : 'text-white/80'
                    }`}>
                    {rule.name}
                  </span>
                  <span className='text-xs px-1.5 py-0.5 bg-green-500/30 text-green-300 rounded-full'>
                    ✓ Active
                  </span>
                  {rule.id === 'momentum_equilibrium' && <span className='text-xs'>⭐</span>}
                </div>
                <p className='text-xs text-white/60 mt-0.5'>
                  {rule.description}
                </p>
                <p className='text-xs text-white/40 mt-0.5'>
                  {rule.performance}
                </p>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
