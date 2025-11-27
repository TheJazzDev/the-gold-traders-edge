import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { Toaster } from "@/components/ui/Toaster";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "The Gold Trader's Edge | XAUUSD Trading Signals",
  description:
    "Professional gold trading signals with real-time analysis, smart execution, and risk management. Mindset, Risk, and Smart Execution.",
  keywords: ["gold", "xauusd", "trading", "signals", "forex", "analysis"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${spaceGrotesk.variable} font-body min-h-screen`}
      >
        <div className="relative min-h-screen">
          <div className="fixed inset-0 bg-linear-to-br from-secondary-950 via-secondary-900 to-secondary-950" />
          <div className="fixed inset-0 bg-[url('/grid.svg')] opacity-5" />
          <div className="fixed top-0 left-1/4 w-96 h-96 bg-primary-500/5 rounded-full blur-3xl" />
          <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />

          <div className="relative z-10">
            <Header />
            <main className="container mx-auto px-4 py-8">{children}</main>
          </div>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
