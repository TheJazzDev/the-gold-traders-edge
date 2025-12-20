import { DashboardHeader } from '@/components/dashboard/dashboard-header';
import { BacktestControls } from '@/components/dashboard/backtest-controls';
import { DashboardFooter } from '@/components/dashboard/dashboard-footer';

export default function DashboardPage() {
  return (
    <div className='min-h-screen bg-linear-to-br from-slate-900 via-purple-900 to-slate-900'>
      {/* Animated background elements */}
      <div className='fixed inset-0 overflow-hidden pointer-events-none'>
        <div className='absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse'></div>
        <div
          className='absolute -bottom-40 -left-40 w-80 h-80 bg-amber-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse'
          style={{ animationDelay: '2s' }}></div>
        <div
          className='absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse'
          style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Header */}
      <DashboardHeader />

      {/* Main Content */}
      <main className='relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8'>
        <BacktestControls />
        <DashboardFooter />
      </main>
    </div>
  );
}
