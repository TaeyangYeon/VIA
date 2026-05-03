/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0a0a0a',
          card: '#111111',
          secondary: '#1a1a1a',
          hover: '#222222',
        },
        border: {
          default: '#2a2a2a',
          emphasis: '#3a3a3a',
        },
        text: {
          primary: '#f5f5f5',
          secondary: '#a0a0a0',
          disabled: '#555555',
        },
        accent: {
          action: '#ffffff',
          success: '#4ade80',
          warning: '#facc15',
          error: '#f87171',
          info: '#60a5fa',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
      },
    },
  },
  plugins: [],
};
