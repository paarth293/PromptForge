import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'PromptForge — The Self-Hardening Forge for AI Agents',
  description: 'Enterprise-grade AI agent security platform: one sentence in, attack-hardened agent out.',
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
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="antialiased min-h-screen font-sans bg-[#F9F5F0] text-[#3D3229] selection:bg-[#C75A3B]/20 selection:text-[#C75A3B]">
        {children}
      </body>
    </html>
  );
}
