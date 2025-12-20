interface ErrorDisplayProps {
  error: string;
}

export function ErrorDisplay({ error }: ErrorDisplayProps) {
  return (
    <div className='mb-8 bg-linear-to-r from-red-500/20 to-red-600/20 backdrop-blur-xl border-2 border-red-500/50 rounded-2xl p-4 sm:p-6 shadow-xl'>
      <div className='flex items-start gap-3 sm:gap-4'>
        <div className='p-2 bg-red-500/30 rounded-full shrink-0'>
          <svg
            className='h-5 w-5 sm:h-6 sm:w-6 text-red-400'
            viewBox='0 0 20 20'
            fill='currentColor'>
            <path
              fillRule='evenodd'
              d='M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z'
              clipRule='evenodd'
            />
          </svg>
        </div>
        <div>
          <h3 className='text-base sm:text-lg font-bold text-red-300'>Error</h3>
          <p className='text-sm sm:text-base text-red-200 mt-1'>{error}</p>
          <p className='text-xs sm:text-sm text-red-300/80 mt-3 bg-black/20 px-3 sm:px-4 py-2 rounded-lg inline-block'>
            Start the API:{' '}
            <code className='font-mono font-bold'>
              cd packages/engine && ./start_api.sh
            </code>
          </p>
        </div>
      </div>
    </div>
  );
}
