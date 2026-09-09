import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PromptForge — The Self-Hardening Forge for AI Agents',
  description: 'The Operating System for AI Agents, Built Entirely Through Prompts.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen font-sans bg-forge-dark text-slate-100">
        {children}
      </body>
    </html>
  );
}
