export function WelcomeState() {
  return (
    <div className='text-center py-12 sm:py-16'>
      <div className='inline-flex items-center justify-center w-20 h-20 sm:w-24 sm:h-24 bg-linear-to-br from-amber-500 to-yellow-500 rounded-full mb-4 sm:mb-6 shadow-2xl shadow-amber-500/30'>
        <span className='text-4xl sm:text-5xl'>📊</span>
      </div>
      <h2 className='text-2xl sm:text-3xl font-bold text-white mb-3 sm:mb-4'>
        Ready to Backtest
      </h2>
      <p className='text-white/60 text-base sm:text-lg max-w-md mx-auto mb-6 sm:mb-8 px-4'>
        Select your preferred timeframe and trading rules above, then click the
        Run button to start the backtest.
      </p>
      <div className='inline-flex items-center gap-2 text-amber-400 text-sm'>
        <svg
          className='w-5 h-5 animate-bounce'
          fill='none'
          viewBox='0 0 24 24'
          stroke='currentColor'>
          <path
            strokeLinecap='round'
            strokeLinejoin='round'
            strokeWidth={2}
            d='M5 10l7-7m0 0l7 7m-7-7v18'
          />
        </svg>
        Configure settings above and click Run Backtest
      </div>
    </div>
  );
}
