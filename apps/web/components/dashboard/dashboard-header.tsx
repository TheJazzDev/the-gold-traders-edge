export function DashboardHeader() {
  return (
    <header className='relative bg-linear-to-r from-amber-600 via-yellow-500 to-amber-500 shadow-2xl'>
      <div className='relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8'>
        <div className='flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 sm:gap-6'>
          <div>
            <h1 className='text-3xl sm:text-4xl md:text-5xl font-black text-white flex items-center gap-2 sm:gap-3 drop-shadow-lg'>
              <span className='text-4xl sm:text-5xl animate-bounce'>🥇</span>
              <span className='bg-clip-text text-transparent bg-linear-to-r from-white via-yellow-100 to-white'>
                The Gold Trader&apos;s Edge
              </span>
            </h1>
            <p className='text-amber-100 mt-2 sm:mt-3 text-base sm:text-lg font-medium'>
              Professional XAUUSD backtesting & signal analytics
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
