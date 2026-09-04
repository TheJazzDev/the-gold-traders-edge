"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/performance", label: "Performance" },
  { href: "/controls", label: "Controls", locked: true },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="relative border-b border-white/10 bg-slate-950/50 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 sm:h-16">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-linear-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <span className="font-serif font-bold text-sm sm:text-base text-white leading-none">Au</span>
            </div>
            <span className="font-bold text-sm sm:text-base text-white">Gold Trader&apos;s Edge</span>
          </Link>

          <div className="flex items-center gap-1 sm:gap-2">
            {LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors",
                    active ? "bg-white/10 text-white" : "text-gray-400 hover:text-white hover:bg-white/5"
                  )}
                >
                  {link.label}
                  {link.locked && <Lock className="w-3 h-3" />}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
