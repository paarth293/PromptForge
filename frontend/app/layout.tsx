import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'PromptForge — The Self-Hardening Forge for AI Agents',
  description: 'The Operating System for AI Agents, Built Entirely Through Prompts.',
  icons: {
    icon: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased min-h-screen font-sans bg-forge-dark text-slate-100">
        {children}
      </body>
    </html>
  );
}
