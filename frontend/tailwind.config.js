/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary  : { DEFAULT: '#1e3a5f', light: '#2563eb', dark: '#0f2340' },
        accent   : { DEFAULT: '#2563eb', light: '#3b82f6' },
        success  : '#10b981',
        warning  : '#f59e0b',
        danger   : '#ef4444',
        risk     : { low: '#10b981', moderate: '#f59e0b', high: '#f97316', critical: '#ef4444' },
      },
      fontFamily: {
        sans : ['Inter', 'system-ui', 'sans-serif'],
        mono : ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}