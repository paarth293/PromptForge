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
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        // PromptForge Professional Yet Warm Palette (Specification v1.0)
        forge: {
          'orange-rust': '#C75A3B',
          'orange-light': '#D97D5E',
          'cream': '#F9F5F0',
          'beige': '#F0E6DC',
          'white-cream': '#FBF8F4',
          'tan-border': '#E8DDD2',
          'success': '#2ECC71',
          'warning': '#F39C12',
          'critical': '#E74C3C',
          'text-primary': '#3D3229',
          'text-secondary': '#666555',
          'text-disabled': '#B0A89E',

          // Functional Aliases
          primary: '#C75A3B',
          secondary: '#D97D5E',
          accent: '#2ECC71',
          danger: '#E74C3C',
          border: '#E8DDD2',
          borderSoft: '#F0E6DC',
          surface: '#FBF8F4',
          surface2: '#F0E6DC',
          dark: '#F9F5F0',
        },
        brand: {
          orange: '#C75A3B',
          'orange-light': '#D97D5E',
          indigo: '#4A5568',
          teal: '#2ECC71',
          gold: '#F39C12',
          red: '#E74C3C',
        },
      },
      fontSize: {
        'display': ['40px', { lineHeight: '1.2', fontWeight: '700' }],
        'h1': ['28px', { lineHeight: '1.3', fontWeight: '600' }],
        'h2': ['20px', { lineHeight: '1.4', fontWeight: '600' }],
        'h3': ['18px', { lineHeight: '1.4', fontWeight: '600' }],
        'body': ['14px', { lineHeight: '1.6', fontWeight: '400' }],
        'body-sm': ['13px', { lineHeight: '1.5', fontWeight: '400' }],
        'label': ['13px', { lineHeight: '1.4', fontWeight: '600' }],
        'caption': ['12px', { lineHeight: '1.5', fontWeight: '500' }],
        'mono': ['13px', { lineHeight: '1.5', fontWeight: '400' }],
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'card-active': '0 8px 24px rgba(0, 0, 0, 0.12)',
        'brand-glow': '0 4px 12px rgba(199, 90, 59, 0.3)',
        'success-glow': '0 4px 12px rgba(46, 204, 113, 0.2)',
        'critical-glow': '0 4px 12px rgba(231, 76, 60, 0.2)',
        'smart-card': '0 2px 8px rgba(0, 0, 0, 0.05), 0 0 0 1px #E8DDD2',
        'smart-card-hover': '0 6px 16px rgba(199, 90, 59, 0.12), 0 0 0 1px #C75A3B',
        panel: '0 1px 3px rgba(0, 0, 0, 0.04)',
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #C75A3B 0%, #D97D5E 100%)',
        'gradient-success': 'linear-gradient(135deg, #2ECC71 0%, #27AE60 100%)',
        'gradient-progress': 'linear-gradient(90deg, #C75A3B 0%, #2ECC71 100%)',
        'gradient-card': 'linear-gradient(180deg, #FBF8F4 0%, #F9F5F0 100%)',
      },
      borderRadius: {
        'sm': '4px',
        'base': '8px',
        'lg': '12px',
        'small': '4px',
        'default': '8px',
        'large': '12px',
      },
    },
  },
  plugins: [],
};
