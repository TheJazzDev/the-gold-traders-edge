export function DashboardFooter() {
  return (
    <div className='text-center text-xs sm:text-sm text-white/40 pt-8 sm:pt-12 mt-6 sm:mt-8 border-t border-white/10'>
      <p className='text-white/60'>
        Built with ❤️ using Next.js, FastAPI, and Claude Code
      </p>
      <p className='mt-2'>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/docs`}
          target='_blank'
          rel='noopener noreferrer'
          className='text-amber-400 hover:text-amber-300 transition-colors'>
          API Documentation
        </a>
        {' • '}
        <a
          href='https://github.com/anthropics/claude-code'
          target='_blank'
          rel='noopener noreferrer'
          className='text-blue-400 hover:text-blue-300 transition-colors'>
          GitHub
        </a>
      </p>
    </div>
  );
}
