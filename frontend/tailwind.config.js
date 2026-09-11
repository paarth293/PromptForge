/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        forge: {
          dark: '#0A0D14',
          surface: '#121826',
          surface2: '#161D2E',
          border: '#232D42',
          borderSoft: '#1B2334',
          primary: '#3B82F6',
          accent: '#10B981',
          danger: '#EF4444',
          warning: '#F59E0B',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(59,130,246,0.15), 0 8px 24px -8px rgba(59,130,246,0.35)',
        'glow-emerald': '0 0 0 1px rgba(16,185,129,0.15), 0 8px 24px -8px rgba(16,185,129,0.35)',
        panel: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 1px 2px 0 rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'grid-fade':
          'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59,130,246,0.12), transparent)',
      },
    },
  },
  plugins: [],
};
