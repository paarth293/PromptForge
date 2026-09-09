/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forge: {
          dark: '#0B0F17',
          surface: '#121826',
          border: '#232D42',
          primary: '#3B82F6',
          accent: '#10B981',
          danger: '#EF4444',
          warning: '#F59E0B'
        }
      }
    },
  },
  plugins: [],
};
