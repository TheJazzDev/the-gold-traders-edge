import { Sidebar } from '@/components/dashboard/Sidebar';
import { Providers } from '@/app/providers';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className="flex h-screen overflow-hidden bg-white dark:bg-gray-950">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </Providers>
  );
}
