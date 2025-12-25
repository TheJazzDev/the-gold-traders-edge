import { Providers } from '@/app/providers';

export default function UserLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Providers>{children}</Providers>;
}
